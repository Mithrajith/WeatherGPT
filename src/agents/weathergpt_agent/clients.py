"""Shared async HTTP client for the agent's tools.

One pooled `httpx.AsyncClient` for the whole process: connection reuse is worth
tens of milliseconds per tool call, and per-call client construction under
concurrency is the classic way to exhaust sockets during a demo.

All tool traffic goes through `backend_get`, which targets the FastAPI service
owned by the backend lead. `open_meteo_get` exists only as the silent fallback
for when that service (or IMD behind it) is down mid-demo.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


class BackendUnavailable(RuntimeError):
    """Our FastAPI/IMD path failed. Callers may try the fallback source."""


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is not None and not _client.is_closed:
        return _client
    async with _client_lock:
        if _client is None or _client.is_closed:
            settings = get_settings()
            _client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.backend.timeout, connect=3.0),
                limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
                headers={"User-Agent": "WeatherGPT-Agent/0.1"},
                follow_redirects=True,
            )
    return _client


async def close_client() -> None:
    """Call from the FastAPI shutdown hook."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _auth_headers() -> dict[str, str]:
    key = get_settings().backend.api_key
    return {"X-API-Key": key} if key else {}


async def backend_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET against our own API. Raises BackendUnavailable on any failure.

    Retries once on a connection/5xx error: IMD's upstream is occasionally slow
    to first byte, and one cheap retry converts most of those into successes.
    """
    settings = get_settings()
    url = f"{settings.backend.base_url}/{path.lstrip('/')}"
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    client = await get_client()

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.get(url, params=clean, headers=_auth_headers())
            if response.status_code >= 500:
                raise BackendUnavailable(f"{url} returned {response.status_code}")
            if response.status_code == 404:
                # A genuine "no data for this location" answer, not an outage.
                return {"status": "not_found", "detail": response.text[:200]}
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, BackendUnavailable, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(0.25)
                continue
    logger.warning("backend_get failed for %s: %s", url, last_error)
    raise BackendUnavailable(str(last_error))


async def open_meteo_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Fallback source. No API key, so it works even if our secrets are wrong."""
    client = await get_client()
    response = await client.get(url, params=params, timeout=6.0)
    response.raise_for_status()
    return response.json()
