"""Backend configuration.

Two data tiers, chosen at request time:

- IMD (api.imd.gov.in) is authoritative and is used whenever IMD_API_KEY is set.
  Its gateway rejects every unauthenticated call with {"error":"API key missing"},
  so without a key it cannot be used at all.
- Open-Meteo needs no key and is live, so the service still returns real
  observations, forecasts and climate normals with nothing configured.

Every response says which tier answered, and hazard responses say whether the
warning is official. That distinction is the whole reason those fields exist: a
threshold we computed ourselves is not an IMD warning and must never be
presented as one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    return value.strip() or None if value else None


def _env_int(key: str, default: int) -> int:
    try:
        return int(_env(key) or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # --- IMD (optional, authoritative) ---
    imd_api_key: str | None = field(default_factory=lambda: _env("IMD_API_KEY"))
    imd_base: str = field(
        default_factory=lambda: (_env("IMD_BASE_URL", "https://api.imd.gov.in/api/v1") or "").rstrip("/")
    )
    # The gateway docs do not state the header name, so it is configurable and we
    # send the key as a query parameter as well. Adjust once you have the key and
    # can see which form the gateway accepts.
    imd_key_header: str = field(default_factory=lambda: _env("IMD_KEY_HEADER", "x-api-key") or "x-api-key")

    # --- Open-Meteo (no key, always available) ---
    om_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    om_geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    om_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"

    # Caching lives here, not in the agent: this service owns the upstreams, so
    # it is the only place that knows how fresh each kind of data really is.
    ttl_current: int = field(default_factory=lambda: _env_int("TTL_CURRENT", 300))
    ttl_forecast: int = field(default_factory=lambda: _env_int("TTL_FORECAST", 1800))
    ttl_warning: int = field(default_factory=lambda: _env_int("TTL_WARNING", 180))
    ttl_climate: int = field(default_factory=lambda: _env_int("TTL_CLIMATE", 86400))
    ttl_geocode: int = field(default_factory=lambda: _env_int("TTL_GEOCODE", 86400))

    http_timeout: float = 15.0
    db_path: str = field(default_factory=lambda: _env("BACKEND_DB", "weathergpt.sqlite3") or "weathergpt.sqlite3")
    api_key: str | None = field(default_factory=lambda: _env("WEATHER_BACKEND_API_KEY"))

    @property
    def imd_enabled(self) -> bool:
        return bool(self.imd_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
