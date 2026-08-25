"""WeatherGPT backend service.

Implements the contract the agent's tools call. Each endpoint tries IMD first
when a key is configured, then falls back to live Open-Meteo data, and always
reports which tier answered in a `source` field. Hazard responses additionally
carry `official`, which is False for anything we derived ourselves.

    uv run --extra backend uvicorn weather_backend.main:app --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import store
from .cache import cache
from .config import get_settings
from .derive import (
    agromet_from_forecast,
    filter_by_severity,
    hazards_from_forecast,
    warnings_from_imd_district,
)
from .sources import (
    IST,
    UpstreamError,
    close_client,
    imd_city_forecast,
    imd_current,
    imd_district_warnings,
    imd_nearest_station,
    om_current,
    om_forecast,
    om_monthly_history,
    resolve_place,
    warmup,
)

logger = logging.getLogger(__name__)

NOT_FOUND: dict[str, Any] = {"status": "not_found"}

WMO_TEXT = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "moderate rain", 65: "heavy rain",
    80: "light rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}

# IMD current_wx weather codes are the WMO ww table; only the common ones matter
# for a spoken answer, the rest fall through to the numeric code.
IMD_WX_TEXT = {
    "05": "haze", "10": "mist", "28": "fog", "29": "thunderstorm",
    "21": "rain", "25": "rain showers", "20": "drizzle", "50": "drizzle",
    "60": "light rain", "63": "moderate rain", "65": "heavy rain",
    "80": "light rain showers", "81": "rain showers", "95": "thunderstorm",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    await warmup()
    settings = get_settings()
    logger.info("backend up. IMD tier: %s", "enabled" if settings.imd_enabled else "disabled (no key)")
    yield
    await close_client()


app = FastAPI(title="WeatherGPT backend", version="0.1.0", lifespan=lifespan)


@app.exception_handler(UpstreamError)
async def upstream_failed(_request: Request, exc: UpstreamError) -> JSONResponse:
    """Turn any upstream failure into a clean 503.

    Without this, an upstream hiccup anywhere outside an endpoint's own try block
    surfaced as a 500 with a traceback. Place resolution runs before every
    endpoint's try block, so one flaky geocode call took out every route. 503 is
    also the signal the agent's client already understands as "fall back".
    """
    logger.warning("upstream failure: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"status": "upstream_unavailable", "detail": str(exc)[:200]},
    )


def _auth(x_api_key: str | None) -> None:
    expected = get_settings().api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="bad or missing X-API-Key")


def _daily_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Open-Meteo parallel arrays -> one dict per day, in our field names."""
    daily = payload.get("daily") or {}
    stamps = daily.get("time") or []
    rows = []
    for i, when in enumerate(stamps):
        def at(key: str) -> Any:
            values = daily.get(key) or []
            return values[i] if i < len(values) else None

        code = at("weather_code")
        rows.append(
            {
                "date": when,
                "temp_min": at("temperature_2m_min"),
                "temp_max": at("temperature_2m_max"),
                "rainfall": at("precipitation_sum"),
                "rain_chance": at("precipitation_probability_max"),
                "wind_max": at("wind_speed_10m_max"),
                "condition": WMO_TEXT.get(int(code), f"code {code}") if code is not None else None,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# weather
# --------------------------------------------------------------------------- #

@app.get("/api/v1/weather/current")
async def current_weather(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    place = await resolve_place(location, lat, lon)
    if not place:
        return NOT_FOUND

    if get_settings().imd_enabled:
        try:
            station = await imd_nearest_station(place["latitude"], place["longitude"])
            if station:
                station_id = str(
                    station.get("Station_Code") or station.get("station_code") or station.get("id")
                )
                observations = await imd_current(station_id)
                if observations:
                    obs = observations[0]
                    code = str(obs.get("Weather Code") or "").strip()
                    return {
                        "source": "IMD current weather (station observation)",
                        "current": {
                            "observed_at": f"{obs.get('Date of Observation')} {obs.get('Time of Observation')} UTC",
                            "condition": IMD_WX_TEXT.get(code, f"weather code {code}"),
                            "temperature": obs.get("Temperature"),
                            "humidity": obs.get("Humidity"),
                            "precipitation": obs.get("Last 24 hrs Rainfall"),
                            "wind_speed": obs.get("Wind Speed"),
                            "station": obs.get("Station") or station.get("Station_Name"),
                        },
                    }
        except UpstreamError as exc:
            logger.warning("IMD current failed, falling back: %s", exc)

    raw = await om_current(place["latitude"], place["longitude"])
    now = raw.get("current") or {}
    code = now.get("weather_code")
    return {
        "source": "Open-Meteo (no IMD key configured)",
        "current": {
            "observed_at": now.get("time"),
            "condition": WMO_TEXT.get(int(code), f"code {code}") if code is not None else None,
            "temperature": now.get("temperature_2m"),
            "feels_like": now.get("apparent_temperature"),
            "humidity": now.get("relative_humidity_2m"),
            "precipitation": now.get("precipitation"),
            "wind_speed": now.get("wind_speed_10m"),
            "station": f"grid point near {place['name']}",
        },
    }


@app.get("/api/v1/weather/forecast")
async def forecast(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    days: int = 3,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    days = max(1, min(days, 7))
    place = await resolve_place(location, lat, lon)
    if not place:
        return NOT_FOUND

    rows = _daily_rows(await om_forecast(place["latitude"], place["longitude"], days))
    source = "Open-Meteo (no IMD key configured)"

    # IMD publishes daily min/max and a worded forecast per day, but no rainfall
    # amount, so its temperatures and wording are overlaid on Open-Meteo rain
    # figures and the source line says exactly that. Mixing sources silently
    # would let the agent credit IMD for numbers IMD never issued.
    if get_settings().imd_enabled:
        try:
            station = await imd_nearest_station(place["latitude"], place["longitude"])
            if station:
                station_id = str(
                    station.get("Station_Code") or station.get("station_code") or station.get("id")
                )
                imd = await imd_city_forecast(station_id)
                for index, row in enumerate(rows, start=1):
                    prefix = "Todays_Forecast" if index == 1 else f"Day_{index}"
                    max_key = "Todays_Forecast_Max_Temp" if index == 1 else f"{prefix}_Max_Temp"
                    min_key = "Todays_Forecast_Min_temp" if index == 1 else f"{prefix}_Min_temp"
                    text_key = "Todays_Forecast" if index == 1 else f"{prefix}_Forecast"
                    if imd.get(max_key) is not None:
                        row["temp_max"] = imd.get(max_key)
                    if imd.get(min_key) is not None:
                        row["temp_min"] = imd.get(min_key)
                    if imd.get(text_key):
                        row["condition"] = str(imd[text_key]).strip().lower()
                source = (
                    f"IMD city forecast for {imd.get('Station_Name')} "
                    "(temperatures and conditions); Open-Meteo (rainfall amounts)"
                )
        except UpstreamError as exc:
            logger.warning("IMD forecast failed, using Open-Meteo only: %s", exc)

    return {"source": source, "place": place["name"], "forecast": rows}


# --------------------------------------------------------------------------- #
# warnings
# --------------------------------------------------------------------------- #

@app.get("/api/v1/warnings/district")
async def district_warnings(
    district: str | None = None,
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    severity_floor: str = "yellow",
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    name = district or location
    place = await resolve_place(name, lat, lon)
    if not place:
        return NOT_FOUND

    if get_settings().imd_enabled:
        try:
            rows = await imd_district_warnings()
            wanted = (district or place["name"] or "").strip().lower()
            match = next(
                (r for r in rows if str(r.get("District", "")).strip().lower() == wanted), None
            )
            if match:
                warnings = filter_by_severity(
                    warnings_from_imd_district(match, place["name"]), severity_floor
                )
                return {
                    "source": "IMD district warning (official)",
                    "official": True,
                    "warnings": warnings,
                }
        except UpstreamError as exc:
            logger.warning("IMD warnings failed, deriving instead: %s", exc)

    rows = _daily_rows(await om_forecast(place["latitude"], place["longitude"], 5))
    derived = filter_by_severity(hazards_from_forecast(rows, place["name"]), severity_floor)
    return {
        "source": (
            "DERIVED risk assessment: Open-Meteo forecast scored against IMD's published "
            "warning thresholds. This is NOT an official IMD warning."
        ),
        "official": False,
        "warnings": derived,
    }


# --------------------------------------------------------------------------- #
# advisory and climate
# --------------------------------------------------------------------------- #

@app.get("/api/v1/advisory/agromet")
async def agromet(
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    crop: str = "other",
    activity: str = "general",
    days: int = 3,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    place = await resolve_place(location, lat, lon)
    if not place:
        return NOT_FOUND

    rows = _daily_rows(await om_forecast(place["latitude"], place["longitude"], max(1, min(days, 7))))
    payload = agromet_from_forecast(rows, crop, activity)
    payload["source"] = (
        "DERIVED advisory from live forecast using IMD rainfall thresholds. "
        "Not an IMD agromet bulletin (that product needs an IMD API key)."
    )
    payload["official"] = False
    return payload


@app.get("/api/v1/climate/trend")
async def climate_trend(
    district: str,
    month: int | None = None,
    metric: str = "rainfall",
    years: int = 10,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    place = await resolve_place(district, None, None)
    if not place:
        return NOT_FOUND

    try:
        stats = await om_monthly_history(
            place["latitude"], place["longitude"], month, max(3, min(years, 30)), metric
        )
    except UpstreamError as exc:
        logger.warning("climate archive failed: %s", exc)
        return NOT_FOUND

    normal, latest = stats["normal"], stats["latest"]
    anomaly = round(latest - normal, 1)
    percent = round((latest / normal) * 100) if normal else None
    month_name = datetime(2000, stats["month"], 1).strftime("%B")
    direction = "wetter than normal" if anomaly > 0 else "drier than normal"
    if metric != "rainfall":
        direction = "warmer than normal" if anomaly > 0 else "cooler than normal"

    return {
        "source": "ERA5 reanalysis via Open-Meteo archive (climatology, not an IMD bulletin)",
        "trend": {
            "period": (
                f"{month_name} {stats['latest_year']}"
                + (" (month still in progress)" if stats["partial"] else "")
                + f", against the {stats['years_compared']}-year mean"
            ),
            "years": stats["years_compared"],
            "normal": normal,
            "latest": latest,
            "anomaly": anomaly,
            "percent_of_normal": percent,
            "direction": direction,
        },
    }


# --------------------------------------------------------------------------- #
# user state
# --------------------------------------------------------------------------- #

class LocationIn(BaseModel):
    location: str
    label: str = "home"
    make_default: bool = False


class SubscriptionIn(BaseModel):
    district: str
    subscribe: bool = True


@app.get("/api/v1/users/{user_id}/locations")
async def get_locations(
    user_id: str, x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> dict[str, Any]:
    _auth(x_api_key)
    return {"locations": store.list_locations(user_id)}


@app.post("/api/v1/users/{user_id}/locations")
async def post_location(
    user_id: str,
    body: LocationIn,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    store.save_location(user_id, body.location, body.label, body.make_default)
    return {"status": "saved", "locations": store.list_locations(user_id)}


@app.post("/api/v1/users/{user_id}/subscriptions")
async def post_subscription(
    user_id: str,
    body: SubscriptionIn,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _auth(x_api_key)
    districts = store.set_subscription(user_id, body.district, body.subscribe)
    return {"status": "ok", "districts": districts}


@app.get("/api/v1/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "now_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "imd_tier": "enabled" if settings.imd_enabled else "disabled (set IMD_API_KEY)",
        "cache": cache.stats(),
        "subscriptions": len(store.all_subscriptions()),
    }
