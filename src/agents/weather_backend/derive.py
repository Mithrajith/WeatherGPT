"""Derived products: hazard assessment and agromet advice.

Both exist because the corresponding IMD products need an API key. When one is
not available, returning nothing would leave the agent unable to answer safety
and farming questions at all, and inventing an "IMD warning" would be dangerous.
So we compute an assessment from live forecast numbers using IMD's own published
thresholds, and label it `official: false` so the agent tells the user it is not
an IMD warning.

IMD 24-hour rainfall categories (mausam.imd.gov.in bulletins):

    heavy            64.5 - 115.5 mm   -> yellow
    very heavy      115.6 - 204.4 mm   -> orange
    extremely heavy      >= 204.5 mm   -> red

Wind and thunderstorm bands follow IMD's nowcast category table, and the heatwave
band uses the plains criterion of 40 degrees Celsius and above.
"""

from __future__ import annotations

from typing import Any

# (lower bound mm, colour, label)
RAIN_BANDS: list[tuple[float, str, str]] = [
    (204.5, "red", "extremely heavy rainfall"),
    (115.6, "orange", "very heavy rainfall"),
    (64.5, "yellow", "heavy rainfall"),
]
WIND_BANDS: list[tuple[float, str, str]] = [
    (87.0, "red", "very severe squall"),
    (62.0, "orange", "severe squall"),
    (41.0, "yellow", "strong surface winds"),
]
HEAT_BANDS: list[tuple[float, str, str]] = [
    (45.0, "red", "severe heat wave conditions"),
    (42.0, "orange", "heat wave conditions"),
    (40.0, "yellow", "hot day"),
]

SEVERITY_ORDER = {"green": 0, "yellow": 1, "orange": 2, "red": 3}

# IMD district warning codes -> plain hazard names (api_reference table 6).
IMD_WARNING_CODES = {
    "1": "no warning",
    "2": "heavy rain",
    "3": "heavy snow",
    "4": "thunderstorm and lightning",
    "5": "hailstorm",
    "6": "dust storm",
    "7": "dust raising winds",
    "8": "strong surface winds",
    "9": "heat wave",
    "10": "hot day",
    "11": "warm night",
    "12": "cold wave",
    "13": "cold day",
    "14": "ground frost",
    "15": "fog",
    "16": "very heavy rain",
    "17": "extremely heavy rain",
}
# IMD colour code -> name. Note table 6 and table 4 number these differently;
# this is table 6 (district warnings): 1 red, 2 orange, 3 yellow, 4 green.
IMD_DISTRICT_COLOURS = {"1": "red", "2": "orange", "3": "yellow", "4": "green"}


def _band(value: float | None, bands: list[tuple[float, str, str]]) -> tuple[str, str] | None:
    if value is None:
        return None
    for threshold, colour, label in bands:
        if value >= threshold:
            return colour, label
    return None


def hazards_from_forecast(rows: list[dict[str, Any]], place: str) -> list[dict[str, Any]]:
    """Apply IMD thresholds to forecast rows. Returns one entry per hazardous day."""
    found: list[dict[str, Any]] = []
    for row in rows:
        for value, bands in (
            (row.get("rainfall"), RAIN_BANDS),
            (row.get("wind_max"), WIND_BANDS),
            (row.get("temp_max"), HEAT_BANDS),
        ):
            hit = _band(value, bands)
            if not hit:
                continue
            colour, label = hit
            found.append(
                {
                    "severity": colour,
                    "hazard": label,
                    "district": place,
                    "valid_from": row.get("date"),
                    "valid_until": row.get("date"),
                    "description": (
                        f"Forecast for {row.get('date')}: rainfall "
                        f"{row.get('rainfall')} millimetres, maximum temperature "
                        f"{row.get('temp_max')} degrees Celsius, wind up to "
                        f"{row.get('wind_max')} kilometres per hour. Assessed against "
                        f"IMD's published warning thresholds."
                    ),
                }
            )
    found.sort(key=lambda w: SEVERITY_ORDER.get(w["severity"], 0), reverse=True)
    return found


def warnings_from_imd_district(row: dict[str, Any], place: str) -> list[dict[str, Any]]:
    """Translate one IMD districtwarning row into our warning shape."""
    out: list[dict[str, Any]] = []
    for day in range(1, 6):
        codes = str(row.get(f"Day_{day}") or "").strip()
        colour = IMD_DISTRICT_COLOURS.get(str(row.get(f"Day{day}_Color") or "").strip(), "green")
        if not codes or codes == "1":
            continue
        hazards = ", ".join(
            IMD_WARNING_CODES.get(code.strip(), f"code {code.strip()}")
            for code in codes.split(",")
            if code.strip()
        )
        out.append(
            {
                "severity": colour,
                "hazard": hazards,
                "district": row.get("District") or place,
                "valid_from": f"day {day} from {row.get('Date')}",
                "valid_until": f"day {day} 0830 IST",
                "description": f"IMD district warning, day {day}: {hazards}.",
            }
        )
    out.sort(key=lambda w: SEVERITY_ORDER.get(w["severity"], 0), reverse=True)
    return out


def filter_by_severity(warnings: list[dict[str, Any]], floor: str) -> list[dict[str, Any]]:
    minimum = SEVERITY_ORDER.get(floor, 1)
    return [w for w in warnings if SEVERITY_ORDER.get(w.get("severity", "green"), 0) >= minimum]


# --------------------------------------------------------------------------- #
# Agromet
# --------------------------------------------------------------------------- #

WET_MM = 10.0        # enough rain that soil work and spraying are affected
HEAVY_MM = 64.5      # IMD heavy-rain threshold: drainage and lodging risk
SPRAY_WIND_KMPH = 20.0   # above this, spray drift wastes chemical

ACTIVITY_WHEN_WET = {
    "spraying": "Postpone spraying: rain within 24 hours washes off the chemical.",
    "irrigation": "Skip irrigation, the rain will cover the crop's need.",
    "sowing": "Hold sowing until the field is workable again.",
    "harvest": "Harvest before the rain if the crop is ready, otherwise wait for a dry spell.",
    "storage": "Move harvested produce under cover and raise it off the floor.",
    "general": "Plan field work around the rain and protect anything already harvested.",
}
ACTIVITY_WHEN_DRY = {
    "spraying": "Good window for spraying while wind stays low.",
    "irrigation": "Irrigate as usual; no useful rain is expected.",
    "sowing": "Conditions suit sowing if soil moisture is adequate.",
    "harvest": "Dry weather suits harvesting and drying.",
    "storage": "No rain risk to stored produce in this window.",
    "general": "A dry window: catch up on field operations.",
}


def agromet_from_forecast(
    rows: list[dict[str, Any]], crop: str, activity: str
) -> dict[str, Any]:
    """Turn a forecast into a field decision using documented rainfall thresholds."""
    rains = [r.get("rainfall") or 0.0 for r in rows]
    total = round(sum(rains), 1)
    peak = max(rains) if rains else 0.0
    winds = [r.get("wind_max") or 0.0 for r in rows]
    wet = peak >= WET_MM

    first_dry = next(
        (r.get("date") for r in rows if (r.get("rainfall") or 0.0) < WET_MM), None
    )
    recommendation = (ACTIVITY_WHEN_WET if wet else ACTIVITY_WHEN_DRY).get(
        activity, ACTIVITY_WHEN_WET["general"]
    )
    if wet and first_dry:
        window = f"next drier day in the window is {first_dry}"
    elif wet:
        window = "no dry day in this window"
    else:
        window = "the whole window is workable"

    risks = []
    if peak >= HEAVY_MM:
        risks.append("waterlogging and crop lodging from heavy rain")
    elif wet:
        risks.append("fungal infection in prolonged wet leaf conditions")
    if activity == "spraying" and max(winds, default=0.0) >= SPRAY_WIND_KMPH:
        risks.append("spray drift in winds above 20 kilometres per hour")
    if not risks:
        risks.append("no significant weather risk in this window")

    return {
        "advisory": {
            "driver": f"{total} millimetres of rain forecast over {len(rows)} days, peak day {peak} millimetres",
            "recommendation": f"{crop}: {recommendation}",
            "window": window,
            "risk": "; ".join(risks),
            "issued_by": "derived from forecast using IMD rainfall thresholds, not an IMD agromet bulletin",
        },
        "forecast_summary": ", ".join(
            f"{r.get('date')}: {r.get('rainfall')} millimetres" for r in rows
        ),
    }
