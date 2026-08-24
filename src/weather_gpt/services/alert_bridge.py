import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi.concurrency import run_in_threadpool

from src.alerts.database import Alert, SessionLocal
from src.alerts.schemas import WarningInput
from src.alerts.alert_service import AlertService

logger = logging.getLogger("weather_gpt.alert_bridge")

# Forecast condition keywords mapped to (warning_type, imd_severity)
_CONDITION_RULES = [
    (("cyclone",), "cyclone", "red"),
    (("thunderstorm", "storm"), "thunderstorm", "orange"),
    (("rain", "drizzle", "shower"), "heavy_rain", "orange"),
]

_HEATWAVE_THRESHOLD_C = 40.0


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _row_to_payload(a: Alert) -> Dict[str, Any]:
    return {
        "event": "weather_alert",
        "alert_id": a.external_warning_id,
        "district": a.district,
        "severity": a.severity,
        "title": a.title,
        "message": a.message,
        "action": a.action,
        "valid_until": _naive_utc(a.valid_until).isoformat(),
    }


async def get_active_alerts(district: str) -> List[Dict[str, Any]]:
    """Return non-expired stored alerts for a district (threadpool-wrapped sync DB)."""
    def _query() -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            rows = (
                db.query(Alert)
                .filter(Alert.district.ilike(district.strip()))
                .filter(Alert.valid_until > now)
                .order_by(Alert.valid_until.asc())
                .all()
            )
            return [_row_to_payload(a) for a in rows]
        finally:
            db.close()

    try:
        return await run_in_threadpool(_query)
    except Exception as e:
        logger.warning(f"Active alert lookup failed for {district}: {e}")
        return []


def _classify_forecast_day(day: Dict[str, Any]) -> tuple | None:
    """Map a forecast day to (warning_type, severity) or None if benign."""
    condition = str(day.get("condition", "")).lower()
    warning_text = str(day.get("warning") or "").lower()
    max_temp = float(day.get("max_temp") or 0.0)

    if max_temp >= _HEATWAVE_THRESHOLD_C:
        return ("heatwave", "orange")
    if day.get("rainfall_probability", 0) >= 70 or "heavy" in warning_text:
        return ("heavy_rain", "orange")
    for keywords, wtype, sev in _CONDITION_RULES:
        if any(k in condition for k in keywords):
            return (wtype, sev)
    return None


async def sync_forecast_to_alerts(location_name: str, forecast_days: List[Dict[str, Any]]) -> int:
    """
    Convert severe forecast days into persisted alerts.
    Duplicates are suppressed by deterministic external_warning_id, and each new
    alert is broadcast to WebSocket subscribers by the alerts service.
    Returns the number of NEW alerts created.
    """
    created = 0
    now = datetime.now(timezone.utc)

    for day in forecast_days:
        classification = _classify_forecast_day(day)
        if classification is None:
            continue

        warning_type, severity = classification
        try:
            day_end = datetime.fromisoformat(str(day["date"])).replace(
                hour=23, minute=59, tzinfo=timezone.utc
            )
        except (KeyError, ValueError):
            continue
        if day_end <= now:
            continue

        payload = WarningInput(
            district=location_name,
            warning_type=warning_type,
            severity=severity,
            description=str(day.get("warning") or f"{day.get('condition', warning_type)} expected on {day['date']}."),
            valid_from=now.isoformat(),
            valid_until=day_end.isoformat(),
            external_warning_id=f"AUTO-{location_name.upper().replace(' ', '-')}-{day['date']}-{warning_type}",
        )

        db = SessionLocal()
        try:
            exists = (
                db.query(Alert)
                .filter(Alert.external_warning_id == payload.external_warning_id)
                .first()
            )
            if not exists:
                await AlertService.process_warning_data(db, payload)
                created += 1
        except ValueError:
            pass
        except Exception as e:
            logger.warning(f"Forecast-to-alert sync failed for {location_name}: {e}")
        finally:
            db.close()

    if created:
        logger.info(f"Auto-generated {created} alert(s) from forecast for {location_name}.")
    return created
