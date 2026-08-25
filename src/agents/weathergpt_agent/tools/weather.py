"""Weather tools: IMD-backed via our FastAPI service, Open-Meteo as fallback.

Contract with the backend lead (agreed hour 1, mirrors the shared OpenAPI doc):

    GET /api/v1/weather/current    ?location=&lat=&lon=
    GET /api/v1/weather/forecast   ?location=&lat=&lon=&days=
    GET /api/v1/warnings/district  ?district=&location=&severity_floor=
    GET /api/v1/advisory/agromet   ?location=&crop=&activity=&days=
    GET /api/v1/climate/trend      ?district=&month=&metric=&years=

Each returns JSON; the formatters in `formatting.py` tolerate both the IMD-shaped
response and the Open-Meteo shape, so a mid-demo failover does not change the
answer's structure.

Caching is *not* here. It used to be a hand-written TTL cache in this package;
it is now LangGraph's node-level cache on the read-only tool node (see
`graph.py`), which means one cache with one eviction rule for every read tool
instead of per-tool bookkeeping.

Every tool is async so a single request can fan out to two tools concurrently,
and every tool catches its own exceptions: a raised exception would be turned
into a generic error by ToolNode, whereas a TOOL_ERROR string tells the model
exactly what is missing and how to degrade.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool

from ..clients import BackendUnavailable, backend_get, open_meteo_get
from ..config import get_settings
from ..schemas import (
    CurrentWeatherInput,
    FarmAdvisoryInput,
    ForecastInput,
    HistoricalTrendInput,
    WarningInput,
)
from . import formatting as fmt

logger = logging.getLogger(__name__)


def _place_label(location: str | None, lat: float | None, lon: float | None) -> str:
    if location:
        return location
    if lat is not None and lon is not None:
        return f"{lat:.3f}, {lon:.3f}"
    return get_settings().default_location


def _needs_location(location: str | None, lat: float | None, lon: float | None) -> bool:
    return not location and (lat is None or lon is None)


_ASK_FOR_LOCATION = (
    "TOOL_ERROR: no location available. Ask the user which city, district or village "
    "they are asking about before calling this tool again."
)


# --------------------------------------------------------------------------- #
# Open-Meteo fallback
# --------------------------------------------------------------------------- #

async def _geocode_fallback(place: str) -> tuple[float, float] | None:
    settings = get_settings()
    try:
        data = await open_meteo_get(
            settings.backend.open_meteo_geocode_url,
            {"name": place, "count": 1, "country": "IN", "language": "en"},
        )
        results = data.get("results") or []
        if not results:
            return None
        return float(results[0]["latitude"]), float(results[0]["longitude"])
    except Exception as exc:  # noqa: BLE001 - fallback must never raise
        logger.warning("geocode fallback failed for %s: %s", place, exc)
        return None


async def _resolve_coords(
    location: str | None, lat: float | None, lon: float | None
) -> tuple[float, float] | None:
    if lat is not None and lon is not None:
        return lat, lon
    if location:
        return await _geocode_fallback(location)
    return None


async def _current_via_fallback(
    location: str | None, lat: float | None, lon: float | None
) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.backend.enable_fallback:
        return None
    coords = await _resolve_coords(location, lat, lon)
    if coords is None:
        return None
    try:
        return await open_meteo_get(
            settings.backend.open_meteo_url,
            {
                "latitude": coords[0],
                "longitude": coords[1],
                "current": (
                    "temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "timezone": "Asia/Kolkata",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("open-meteo current fallback failed: %s", exc)
        return None


async def _forecast_via_fallback(
    location: str | None, lat: float | None, lon: float | None, days: int
) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.backend.enable_fallback:
        return None
    coords = await _resolve_coords(location, lat, lon)
    if coords is None:
        return None
    try:
        data = await open_meteo_get(
            settings.backend.open_meteo_url,
            {
                "latitude": coords[0],
                "longitude": coords[1],
                "daily": (
                    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "precipitation_probability_max,weather_code"
                ),
                "forecast_days": days,
                "timezone": "Asia/Kolkata",
            },
        )
        return {"forecast": data.get("daily", {})}
    except Exception as exc:  # noqa: BLE001
        logger.warning("open-meteo forecast fallback failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #

async def get_current_weather(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Live observed weather right now from the nearest IMD station."""
    if _needs_location(location, latitude, longitude):
        return _ASK_FOR_LOCATION

    place = _place_label(location, latitude, longitude)
    try:
        payload = await backend_get(
            "/api/v1/weather/current",
            {"location": location, "lat": latitude, "lon": longitude},
        )
        if payload.get("status") == "not_found":
            return fmt.tool_error(
                "current weather", f"IMD has no station data for {place}"
            )
        return fmt.format_current(payload, place)
    except BackendUnavailable as exc:
        fallback = await _current_via_fallback(location, latitude, longitude)
        if fallback:
            return fmt.format_current(fallback, place, degraded=True)
        return fmt.tool_error("current weather", str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_current_weather failed")
        return fmt.tool_error("current weather", str(exc))


async def get_forecast(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    days: int = 3,
) -> str:
    """IMD forecast for the next 1 to 7 days: temperature, rainfall, rain chance."""
    if _needs_location(location, latitude, longitude):
        return _ASK_FOR_LOCATION

    days = max(1, min(int(days), 7))
    place = _place_label(location, latitude, longitude)
    try:
        payload = await backend_get(
            "/api/v1/weather/forecast",
            {
                "location": location,
                "lat": latitude,
                "lon": longitude,
                "days": days,
            },
        )
        if payload.get("status") == "not_found":
            return fmt.tool_error("forecast", f"IMD has no forecast for {place}")
        return fmt.format_forecast(payload, place, days)
    except BackendUnavailable as exc:
        fallback = await _forecast_via_fallback(location, latitude, longitude, days)
        if fallback:
            return fmt.format_forecast(fallback, place, days, degraded=True)
        return fmt.tool_error("forecast", str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_forecast failed")
        return fmt.tool_error("forecast", str(exc))


async def get_district_warnings(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    district: str | None = None,
    severity_floor: str = "yellow",
) -> str:
    """Active IMD colour-coded warnings and nowcasts for a district.

    Covers heavy rain, thunderstorm, heatwave, cyclone and flood advisories.
    """
    if district is None and _needs_location(location, latitude, longitude):
        return _ASK_FOR_LOCATION

    place = district or _place_label(location, latitude, longitude)
    try:
        payload = await backend_get(
            "/api/v1/warnings/district",
            {
                "district": district,
                "location": location,
                "lat": latitude,
                "lon": longitude,
                "severity_floor": severity_floor,
            },
        )
        if payload.get("status") == "not_found":
            return (
                f"Active warnings for {place}\nsource: IMD\n"
                "no warning record found for this district"
            )
        return fmt.format_warnings(payload, place)
    except BackendUnavailable as exc:
        # No fallback here on purpose. Open-Meteo has no IMD warning equivalent,
        # and inventing a hazard status is the worst failure mode we could ship.
        return fmt.tool_error(
            "official warnings",
            f"{exc}. Warnings have no fallback source, so tell the user to check "
            "mausam.imd.gov.in or call the NDMA helpline 1078 for hazard status.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_district_warnings failed")
        return fmt.tool_error("official warnings", str(exc))


async def get_farm_advisory(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    crop: str = "other",
    activity: str = "general",
    days: int = 3,
) -> str:
    """Agromet advisory for a farmer: weather turned into a field decision.

    Use for sowing, irrigation, spraying, harvest and storage questions.
    """
    if _needs_location(location, latitude, longitude):
        return _ASK_FOR_LOCATION

    days = max(1, min(int(days), 7))
    place = _place_label(location, latitude, longitude)
    try:
        payload = await backend_get(
            "/api/v1/advisory/agromet",
            {
                "location": location,
                "lat": latitude,
                "lon": longitude,
                "crop": crop,
                "activity": activity,
                "days": days,
            },
        )
        if payload.get("status") == "not_found":
            # Degrade to raw forecast rather than dead-ending the farmer: the
            # LLM can still reason about spraying from rain and wind numbers.
            forecast = await get_forecast(location, latitude, longitude, days)
            return (
                "No IMD agromet bulletin for this block. Use the forecast below and "
                f"reason about the {activity} decision for {crop} from it, saying "
                "clearly that this is your interpretation and not an official "
                f"advisory.\n{forecast}"
            )
        return fmt.format_advisory(payload, place, crop, activity)
    except BackendUnavailable as exc:
        return fmt.tool_error("agromet advisory", str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_farm_advisory failed")
        return fmt.tool_error("agromet advisory", str(exc))


async def get_historical_trend(
    district: str,
    month: int | None = None,
    metric: str = "rainfall",
    years: int = 10,
) -> str:
    """Compare recent rainfall or temperature against the multi-year normal.

    Historical district records only. Never use this to answer about the future.
    """
    try:
        payload = await backend_get(
            "/api/v1/climate/trend",
            {
                "district": district,
                "month": month,
                "metric": metric,
                "years": years,
            },
        )
        if payload.get("status") == "not_found":
            return fmt.tool_error(
                "historical trend", f"no district records held for {district}"
            )
        return fmt.format_trend(payload, district, metric)
    except BackendUnavailable as exc:
        return fmt.tool_error("historical trend", str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_historical_trend failed")
        return fmt.tool_error("historical trend", str(exc))


# --------------------------------------------------------------------------- #
# LangChain tool objects
# --------------------------------------------------------------------------- #

CURRENT_WEATHER_TOOL = StructuredTool.from_function(
    coroutine=get_current_weather,
    name="get_current_weather",
    description=(
        "Live observed weather from the nearest IMD station: temperature, feels-like, "
        "humidity, rain in the last hour, wind. Use for 'right now' questions only."
    ),
    args_schema=CurrentWeatherInput,
)

FORECAST_TOOL = StructuredTool.from_function(
    coroutine=get_forecast,
    name="get_forecast",
    description=(
        "IMD forecast for 1 to 7 days ahead with min/max temperature, rainfall in "
        "millimetres and rain probability. Use for any future weather question."
    ),
    args_schema=ForecastInput,
)

WARNINGS_TOOL = StructuredTool.from_function(
    coroutine=get_district_warnings,
    name="get_district_warnings",
    description=(
        "Active IMD colour-coded warnings and nowcasts for a district, covering heavy "
        "rain, thunderstorm, heatwave, cyclone and flood. Use for any safety, hazard "
        "or alert question. This is the only authoritative hazard source; it has no "
        "fallback, so never substitute your own judgement for its result."
    ),
    args_schema=WarningInput,
)

FARM_ADVISORY_TOOL = StructuredTool.from_function(
    coroutine=get_farm_advisory,
    name="get_farm_advisory",
    description=(
        "IMD agromet advisory turning the forecast into a field action for a crop: "
        "sowing, irrigation, spraying, harvest or storage. Use for farming decisions."
    ),
    args_schema=FarmAdvisoryInput,
)

HISTORICAL_TREND_TOOL = StructuredTool.from_function(
    coroutine=get_historical_trend,
    name="get_historical_trend",
    description=(
        "Historical district rainfall or temperature versus the multi-year normal, for "
        "questions about typical or past climate. Not a forecast source."
    ),
    args_schema=HistoricalTrendInput,
)

WEATHER_TOOLS = [
    CURRENT_WEATHER_TOOL,
    FORECAST_TOOL,
    WARNINGS_TOOL,
    FARM_ADVISORY_TOOL,
    HISTORICAL_TREND_TOOL,
]
