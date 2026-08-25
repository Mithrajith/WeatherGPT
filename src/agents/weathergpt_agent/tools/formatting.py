"""Tool-result formatting.

Tools return compact text, not raw JSON. Two reasons:

1. Token cost and latency. An IMD 7-day payload is a few thousand tokens of
   nested JSON; the same information is ~120 tokens as labelled lines.
2. Grounding accuracy. Models misread deeply nested keys and pick the wrong
   day's value. Flat, explicitly labelled lines are much harder to misattribute.

Every formatter marks missing values as "unavailable" rather than dropping the
field, so the model can say what it does not know instead of quietly skipping it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

UNAVAILABLE = "unavailable"

WMO_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "light rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def describe_code(code: Any) -> str:
    try:
        return WMO_CODES.get(int(code), f"weather code {code}")
    except (TypeError, ValueError):
        return UNAVAILABLE


def first(*values: Any) -> Any:
    """First value that is actually present, treating 0 as present.

    Written because `a or b` is wrong here: rainfall of 0.0 is the most common
    real answer to "will it rain", and `0.0 or None` is None, which would report
    "unavailable" for a perfectly good forecast of no rain.
    """
    for value in values:
        if value is not None and value != "":
            return value
    return None


def num(value: Any, unit: str = "", digits: int = 1) -> str:
    """Format a number with its unit, or 'unavailable' if it is missing."""
    if value is None or value == "":
        return UNAVAILABLE
    try:
        rounded = round(float(value), digits)
        text = f"{rounded:g}"
    except (TypeError, ValueError):
        text = str(value)
    return f"{text} {unit}".strip()


IST = timezone(timedelta(hours=5, minutes=30))


def day_name(value: Any) -> str:
    """Label a forecast row relative to today: 'tomorrow (Tuesday 26 Aug)'.

    The relative word is not decoration. A forecast list starts with *today*, and
    a model asked "will it rain tomorrow" will happily read row one and answer
    with today's numbers. Naming the day removes the guess: this was an actual
    off-by-one in testing, on the most common question the product gets.
    """
    if not value:
        return UNAVAILABLE
    try:
        if isinstance(value, datetime):
            parsed = value.date()
        elif isinstance(value, date):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return str(value)

    offset = (parsed - datetime.now(IST).date()).days
    label = {0: "today", 1: "tomorrow", 2: "day after tomorrow"}.get(offset)
    stamp = parsed.strftime("%A %d %b")
    return f"{label} ({stamp})" if label else stamp


def lines(pairs: Iterable[tuple[str, str]]) -> str:
    return "\n".join(f"{label}: {value}" for label, value in pairs)


def header(title: str, place: str, source: str, degraded: bool = False) -> str:
    # Not "IMD (fallback global model)": that reads as IMD data with a footnote,
    # and the model then credits IMD for numbers IMD never issued.
    src = "fallback global model, NOT IMD data" if degraded else source
    return f"{title} for {place}\nsource: {src}"


def format_current(payload: dict[str, Any], place: str, degraded: bool = False) -> str:
    obs = payload.get("current") or payload.get("observation") or payload
    body = lines(
        [
            (
                "observed at",
                str(first(obs.get("time"), obs.get("observed_at"), UNAVAILABLE)),
            ),
            ("conditions", first(obs.get("condition"), describe_code(obs.get("weather_code")))),
            ("temperature", num(first(obs.get("temperature"), obs.get("temperature_2m")), "C")),
            (
                "feels like",
                num(first(obs.get("feels_like"), obs.get("apparent_temperature")), "C"),
            ),
            (
                "humidity",
                num(first(obs.get("humidity"), obs.get("relative_humidity_2m")), "percent", 0),
            ),
            ("rain last hour", num(obs.get("precipitation"), "mm")),
            (
                "wind",
                num(first(obs.get("wind_speed"), obs.get("wind_speed_10m")), "km/h"),
            ),
            ("station", str(obs.get("station") or UNAVAILABLE)),
        ]
    )
    return f"{header('Current conditions', place, payload.get('source') or 'IMD', degraded)}\n{body}"


def format_forecast(
    payload: dict[str, Any], place: str, days: int, degraded: bool = False
) -> str:
    raw_days = payload.get("forecast") or payload.get("days") or []
    if isinstance(raw_days, dict):  # Open-Meteo style parallel arrays
        raw_days = _transpose_daily(raw_days)

    rows: list[str] = []
    for entry in list(raw_days)[:days]:
        rows.append(
            " | ".join(
                [
                    day_name(first(entry.get("date"), entry.get("time"))),
                    f"min {num(first(entry.get('temp_min'), entry.get('temperature_2m_min')), 'C', 0)}",
                    f"max {num(first(entry.get('temp_max'), entry.get('temperature_2m_max')), 'C', 0)}",
                    f"rain {num(first(entry.get('rainfall'), entry.get('precipitation_sum')), 'mm')}",
                    f"rain chance {num(first(entry.get('rain_chance'), entry.get('precipitation_probability_max')), 'percent', 0)}",
                    first(entry.get("condition"), describe_code(entry.get("weather_code"))),
                ]
            )
        )

    if not rows:
        return f"{header('Forecast', place, payload.get('source') or 'IMD', degraded)}\nno forecast data returned"
    return (
        f"{header(f'{len(rows)}-day forecast', place, payload.get('source') or 'IMD', degraded)}\n"
        + "\n".join(rows)
    )


def _transpose_daily(daily: dict[str, Any]) -> list[dict[str, Any]]:
    """Open-Meteo returns {'time': [...], 'temperature_2m_max': [...]}."""
    times = daily.get("time") or []
    out: list[dict[str, Any]] = []
    for i, when in enumerate(times):
        row: dict[str, Any] = {"date": when}
        for key, values in daily.items():
            if key == "time" or not isinstance(values, list) or i >= len(values):
                continue
            row[key] = values[i]
        out.append(row)
    return out


def format_warnings(payload: dict[str, Any], place: str) -> str:
    source = payload.get("source") or "IMD"
    # `official` is False when the backend scored a forecast against IMD's
    # thresholds instead of reading an IMD bulletin. The model has to pass that
    # distinction on, so it is stated as a line the model cannot miss rather
    # than buried in the source string.
    official = payload.get("official")
    status = (
        "official IMD warning"
        if official is True
        else "UNOFFICIAL derived risk assessment, not an IMD warning"
        if official is False
        else "unknown provenance"
    )
    warnings = payload.get("warnings") or payload.get("alerts") or []
    if not warnings:
        return (
            f"{header('Active warnings', place, source)}\n"
            f"status: {status}\n"
            "no active warning above the requested severity"
        )
    blocks: list[str] = []
    for w in warnings:
        blocks.append(
            lines(
                [
                    ("severity", str(w.get("severity") or w.get("colour") or UNAVAILABLE)),
                    ("hazard", str(w.get("hazard") or w.get("type") or UNAVAILABLE)),
                    ("district", str(w.get("district") or place)),
                    ("valid from", str(w.get("valid_from") or UNAVAILABLE)),
                    ("valid until", str(w.get("valid_until") or UNAVAILABLE)),
                    ("text", str(w.get("description") or w.get("text") or UNAVAILABLE)),
                ]
            )
        )
    return (
        f"{header('Active warnings', place, source)}\nstatus: {status}\n"
        + "\n--\n".join(blocks)
    )


def format_advisory(
    payload: dict[str, Any], place: str, crop: str, activity: str
) -> str:
    advisory = payload.get("advisory") or {}
    body = lines(
        [
            ("crop", crop),
            ("activity asked about", activity),
            ("weather driver", str(advisory.get("driver") or UNAVAILABLE)),
            ("recommendation", str(advisory.get("recommendation") or UNAVAILABLE)),
            ("timing window", str(advisory.get("window") or UNAVAILABLE)),
            ("risk", str(advisory.get("risk") or UNAVAILABLE)),
            ("issued by", str(advisory.get("issued_by") or "IMD agromet")),
        ]
    )
    forecast_hint = payload.get("forecast_summary")
    if forecast_hint:
        body += f"\nsupporting forecast: {forecast_hint}"
    source = payload.get("source") or "IMD"
    return f"{header('Agromet advisory', place, source)}\n{body}"


def format_trend(payload: dict[str, Any], district: str, metric: str) -> str:
    stats = payload.get("trend") or payload
    unit = "mm" if metric == "rainfall" else "C"
    source = payload.get("source") or "IMD district records"
    return f"Historical {metric} trend for {district}\nsource: {source}\n" + lines(
        [
            ("period", str(stats.get("period") or UNAVAILABLE)),
            ("years averaged", num(stats.get("years"), "", 0)),
            ("long-period normal", num(stats.get("normal"), unit)),
            ("latest value", num(stats.get("latest"), unit)),
            ("difference from normal", num(stats.get("anomaly"), unit)),
            ("percent of normal", num(stats.get("percent_of_normal"), "percent", 0)),
            ("direction", str(stats.get("direction") or UNAVAILABLE)),
        ]
    )


def tool_error(what: str, detail: str) -> str:
    """Uniform failure shape so the model reliably recognises a dead tool."""
    return (
        f"TOOL_ERROR while fetching {what}: {detail}\n"
        "Tell the user this data is temporarily unavailable, say which part you could "
        "not get, and do not substitute a guessed value."
    )
