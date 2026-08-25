"""Tool argument schemas.

These docstrings and field descriptions are the *actual* interface the LLM
programs against, so they are written for the model, not for us: state the unit,
the allowed range, and what to do when the value is unknown. Most tool-calling
failures in practice are underspecified argument descriptions, not weak models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_FORECAST_DAYS = 7

SUPPORTED_CROPS = (
    "rice",
    "wheat",
    "maize",
    "cotton",
    "sugarcane",
    "groundnut",
    "millet",
    "pulses",
    "banana",
    "coconut",
    "tomato",
    "onion",
    "chilli",
    "tea",
    "coffee",
    "other",
)


class LocationInput(BaseModel):
    """Location, given either by name or by coordinates."""

    location: str | None = Field(
        default=None,
        description=(
            "Place name in India, for example 'Coimbatore' or 'Nashik district'. "
            "Leave empty only if you are passing latitude and longitude instead."
        ),
    )
    latitude: float | None = Field(
        default=None, ge=-90, le=90, description="Decimal degrees north. Optional."
    )
    longitude: float | None = Field(
        default=None, ge=-180, le=180, description="Decimal degrees east. Optional."
    )

    @field_validator("location")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) and v.strip() else None


class CurrentWeatherInput(LocationInput):
    """Live observed conditions from the nearest IMD station."""


class ForecastInput(LocationInput):
    """IMD forecast for the next 1 to 7 days."""

    days: int = Field(
        default=3,
        ge=1,
        le=MAX_FORECAST_DAYS,
        description=(
            "Number of days to return, counting today as day 1. So: 1 for today "
            "only, 2 to cover tomorrow, 3 for a short outlook, 7 for a week. Each "
            "row comes back labelled 'today' or 'tomorrow', so read the label."
        ),
    )


class WarningInput(LocationInput):
    """Active IMD nowcasts and colour-coded warnings for a district."""

    district: str | None = Field(
        default=None,
        description=(
            "District name if the user named one, for example 'Thanjavur'. If you only "
            "know the city, leave this empty and pass the city in 'location' instead."
        ),
    )
    severity_floor: Literal["green", "yellow", "orange", "red"] = Field(
        default="yellow",
        description=(
            "Lowest severity to return. Keep the default 'yellow' so routine green "
            "entries do not crowd out the answer. Use 'green' only if the user "
            "explicitly asks for all advisories."
        ),
    )


class FarmAdvisoryInput(LocationInput):
    """Agromet advisory: weather translated into a field action."""

    crop: str = Field(
        default="other",
        description=(
            "Crop the user is asking about, lowercase. Known crops: "
            + ", ".join(SUPPORTED_CROPS)
            + ". Use 'other' if the user did not say."
        ),
    )
    activity: Literal[
        "sowing", "irrigation", "spraying", "harvest", "storage", "general"
    ] = Field(
        default="general",
        description=(
            "The field operation the user is deciding about. Pick 'general' if they "
            "asked broadly, for example 'what should I do about the weather'."
        ),
    )
    days: int = Field(
        default=3,
        ge=1,
        le=MAX_FORECAST_DAYS,
        description="Planning window in days. Three days suits most field decisions.",
    )

    @field_validator("crop")
    @classmethod
    def _normalise_crop(cls, v: str) -> str:
        return (v or "other").strip().lower() or "other"


class HistoricalTrendInput(BaseModel):
    """Multi-year rainfall and temperature normals for a district.

    Backed by a Postgres aggregation over IMD district data, not a forecast
    model. Use it for 'is this year drier than usual', never for the future.
    """

    district: str = Field(
        description="District or city name, for example 'Pune'. Required."
    )
    month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description=(
            "Month as a number, 1 for January. Leave empty to compare the whole year."
        ),
    )
    metric: Literal["rainfall", "temperature"] = Field(
        default="rainfall",
        description="Which variable to trend. Rainfall is the usual question in India.",
    )
    years: int = Field(
        default=10,
        ge=3,
        le=30,
        description="How many past years to average for the normal.",
    )


class SavedLocationsInput(BaseModel):
    """Read the locations this user has saved.

    No arguments: the user id is injected from RunnableConfig, so the model never
    sees it and cannot invent one.
    """


class SaveLocationInput(BaseModel):
    """Save or update a location for this user."""

    location: str = Field(description="Place name exactly as the user said it.")
    label: str = Field(
        default="home",
        description="Short label such as 'home', 'farm', 'field 2'. Defaults to 'home'.",
    )
    make_default: bool = Field(
        default=False,
        description="True if this should become the location used when none is named.",
    )


class SubscribeAlertsInput(BaseModel):
    """Subscribe or unsubscribe this user from push warnings for a district."""

    district: str = Field(description="District to watch for warnings.")
    subscribe: bool = Field(
        default=True,
        description="True to subscribe, False to unsubscribe. Confirm back either way.",
    )
