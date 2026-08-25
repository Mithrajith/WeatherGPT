"""Upstream data sources: IMD when a key is configured, Open-Meteo always.

Open-Meteo functions are verified live. The IMD functions are written from the
published field reference at api.imd.gov.in/public/api_reference.html but are
**unverified**, because the gateway refuses every unauthenticated request. They
are shaped so that any failure raises `UpstreamError` and the caller falls back
to Open-Meteo, which means a wrong guess about IMD's auth header degrades to
working public data instead of a broken endpoint.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from .cache import cache
from .config import get_settings

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

_client: httpx.AsyncClient | None = None


class UpstreamError(RuntimeError):
    """An upstream refused or failed. Caller decides whether to fall back."""


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout, connect=5.0),
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
            headers={"User-Agent": "WeatherGPT-Backend/0.1"},
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def _get_json(url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    """GET JSON with one cheap retry.

    The public geocoder occasionally drops a connection under repeated use, and a
    single retry converts most of those into successes instead of a failed tool
    call the user has to notice.
    """
    client = await get_client()
    clean = {k: v for k, v in params.items() if v is not None}
    last: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.get(url, params=clean, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt == 0:
                await asyncio.sleep(0.4)
    raise UpstreamError(f"{url}: {last}") from last


# --------------------------------------------------------------------------- #
# IMD  (authoritative, requires IMD_API_KEY)
# --------------------------------------------------------------------------- #

async def imd_get(path: str, params: dict[str, Any] | None = None) -> Any:
    settings = get_settings()
    if not settings.imd_enabled:
        raise UpstreamError("IMD_API_KEY not configured")
    # Key sent both ways because the public reference does not document which the
    # gateway expects; harmless duplication, and one of them will be right.
    headers = {settings.imd_key_header: settings.imd_api_key or ""}
    merged = {"api_key": settings.imd_api_key, **(params or {})}
    return await _get_json(f"{settings.imd_base}/{path.lstrip('/')}", merged, headers)


async def imd_station_map() -> list[dict[str, Any]]:
    """Station id -> name/lat/lon, used to resolve a place to an IMD station."""
    settings = get_settings()

    async def fetch() -> list[dict[str, Any]]:
        data = await imd_get("cityforecast_mapping")
        return data if isinstance(data, list) else data.get("data", [])

    return await cache.get_or_set("imd:station_map", settings.ttl_climate, fetch)


def _num(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


async def imd_nearest_station(lat: float, lon: float) -> dict[str, Any] | None:
    """Closest IMD city station by squared degrees. Good enough at city scale."""
    stations = await imd_station_map()
    best, best_d = None, float("inf")
    for station in stations:
        slat = _num(station.get("Latitude") or station.get("latitude"))
        slon = _num(station.get("Longitude") or station.get("longitude"))
        if slat is None or slon is None:
            continue
        d = (slat - lat) ** 2 + (slon - lon) ** 2
        if d < best_d:
            best, best_d = station, d
    return best


async def imd_city_forecast(station_id: str) -> dict[str, Any]:
    data = await imd_get("cityforecast", {"id": station_id})
    rows = data if isinstance(data, list) else data.get("data", [data])
    if not rows:
        raise UpstreamError("IMD returned no forecast rows")
    return rows[0]


async def imd_current(station_id: str | None = None) -> list[dict[str, Any]]:
    data = await imd_get("current_wx", {"id": station_id} if station_id else None)
    return data if isinstance(data, list) else data.get("data", [])


async def imd_district_warnings() -> list[dict[str, Any]]:
    settings = get_settings()

    async def fetch() -> list[dict[str, Any]]:
        data = await imd_get("districtwarning")
        return data if isinstance(data, list) else data.get("data", [])

    return await cache.get_or_set("imd:districtwarning", settings.ttl_warning, fetch)


async def imd_district_rainfall(obj_id: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()

    async def fetch() -> list[dict[str, Any]]:
        data = await imd_get("districtrainfall", {"id": obj_id} if obj_id else None)
        return data if isinstance(data, list) else data.get("data", [])

    return await cache.get_or_set(
        f"imd:districtrainfall:{obj_id or 'all'}", settings.ttl_climate, fetch
    )


# --------------------------------------------------------------------------- #
# Open-Meteo  (no key, live, verified)
# --------------------------------------------------------------------------- #

async def geocode(place: str) -> dict[str, Any] | None:
    settings = get_settings()

    async def fetch() -> dict[str, Any] | None:
        data = await _get_json(
            settings.om_geocode_url,
            {"name": place, "count": 1, "country": "IN", "language": "en"},
        )
        results = data.get("results") or []
        if not results:
            return None
        top = results[0]
        return {
            "name": top.get("name"),
            "admin1": top.get("admin1"),
            "admin2": top.get("admin2"),
            "latitude": float(top["latitude"]),
            "longitude": float(top["longitude"]),
        }

    return await cache.get_or_set(f"geo:{place.lower()}", settings.ttl_geocode, fetch)


async def om_current(lat: float, lon: float) -> dict[str, Any]:
    settings = get_settings()

    async def fetch() -> dict[str, Any]:
        return await _get_json(
            settings.om_forecast_url,
            {
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "timezone": "Asia/Kolkata",
            },
        )

    return await cache.get_or_set(f"om:cur:{lat:.3f},{lon:.3f}", settings.ttl_current, fetch)


async def om_forecast(lat: float, lon: float, days: int) -> dict[str, Any]:
    settings = get_settings()

    async def fetch() -> dict[str, Any]:
        return await _get_json(
            settings.om_forecast_url,
            {
                "latitude": lat,
                "longitude": lon,
                "daily": (
                    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "precipitation_probability_max,weather_code,wind_speed_10m_max"
                ),
                "forecast_days": max(1, min(days, 7)),
                "timezone": "Asia/Kolkata",
            },
        )

    return await cache.get_or_set(
        f"om:fc:{lat:.3f},{lon:.3f}:{days}", settings.ttl_forecast, fetch
    )


async def om_monthly_history(
    lat: float, lon: float, month: int | None, years: int, metric: str
) -> dict[str, Any]:
    """Real climate normals from the ERA5 reanalysis archive.

    ERA5 lags about five days, so the current month is partial and is reported as
    such rather than silently compared against a full-month normal.
    """
    settings = get_settings()
    today = datetime.now(IST).date()
    first_year = today.year - years
    variable = "precipitation_sum" if metric == "rainfall" else "temperature_2m_mean"

    async def fetch() -> dict[str, Any]:
        return await _get_json(
            settings.om_archive_url,
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": f"{first_year}-01-01",
                "end_date": (today - timedelta(days=6)).isoformat(),
                "daily": variable,
                "timezone": "Asia/Kolkata",
            },
        )

    raw = await cache.get_or_set(
        f"om:hist:{lat:.2f},{lon:.2f}:{month}:{years}:{metric}", settings.ttl_climate, fetch
    )

    daily = raw.get("daily") or {}
    stamps: list[str] = daily.get("time") or []
    values: list[float | None] = daily.get(variable) or []

    target_month = month or today.month
    per_year: dict[int, list[float]] = {}
    for stamp, value in zip(stamps, values):
        if value is None:
            continue
        try:
            when = date.fromisoformat(stamp)
        except ValueError:
            continue
        if when.month != target_month:
            continue
        per_year.setdefault(when.year, []).append(float(value))

    def collapse(samples: list[float]) -> float:
        # Rain accumulates over the month; temperature averages over it.
        return sum(samples) if metric == "rainfall" else sum(samples) / len(samples)

    totals = {year: collapse(samples) for year, samples in per_year.items() if samples}
    if not totals:
        raise UpstreamError("archive returned no data for that month")

    latest_year = max(totals)
    history = [v for y, v in totals.items() if y != latest_year]
    normal = sum(history) / len(history) if history else totals[latest_year]
    latest = totals[latest_year]
    days_seen = len(per_year.get(latest_year, []))

    return {
        "month": target_month,
        "years_compared": len(history),
        "normal": round(normal, 1),
        "latest": round(latest, 1),
        "latest_year": latest_year,
        "days_in_latest": days_seen,
        "partial": target_month == today.month and days_seen < 25,
    }


async def resolve_place(
    location: str | None, lat: float | None, lon: float | None
) -> dict[str, Any] | None:
    """Turn either form of location input into coordinates plus a display name."""
    if lat is not None and lon is not None:
        return {"name": location or f"{lat:.3f}, {lon:.3f}", "latitude": lat, "longitude": lon}
    if location:
        return await geocode(location)
    return None


async def warmup() -> None:
    """Touch the no-key upstream once at startup so the first user request is warm."""
    try:
        await geocode("Coimbatore")
    except UpstreamError as exc:  # pragma: no cover
        logger.warning("warmup failed (offline?): %s", exc)


__all__ = [
    "UpstreamError",
    "close_client",
    "geocode",
    "imd_city_forecast",
    "imd_current",
    "imd_district_rainfall",
    "imd_district_warnings",
    "imd_nearest_station",
    "om_current",
    "om_forecast",
    "om_monthly_history",
    "resolve_place",
    "warmup",
]
