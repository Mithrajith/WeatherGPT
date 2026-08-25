"""Profile tools: the structured (Postgres) side of the router.

This is the second leg of the query-routing pattern. Weather facts come from
live IMD endpoints; user state (saved locations, alert subscriptions) comes from
Postgres behind the same FastAPI service. The LLM decides which leg a question
needs, and some questions ("alert me for my farm district") need both.

`user_id` is taken from `RunnableConfig`, not from the tool arguments. LangChain
injects any parameter annotated `RunnableConfig` and hides it from the schema the
model sees, so the model cannot supply a user id at all — it never learns the
field exists. That matters because a hallucinated id here would write to another
user's row.

The annotation has to be exactly `RunnableConfig`. Writing `RunnableConfig | None`
silently defeats the injection: the parameter stays None, every call falls back to
"anonymous", and all users end up sharing one profile. It looks like it works,
because reads and writes agree with each other on the wrong key.

Contract with the backend lead:

    GET  /api/v1/users/{user_id}/locations
    POST /api/v1/users/{user_id}/locations        {location, label, make_default}
    POST /api/v1/users/{user_id}/subscriptions    {district, subscribe}
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool

from ..clients import BackendUnavailable, backend_get, get_client
from ..config import get_settings
from ..schemas import SavedLocationsInput, SaveLocationInput, SubscribeAlertsInput
from . import formatting as fmt

logger = logging.getLogger(__name__)


def _user_id(config: RunnableConfig | None) -> str:
    return ((config or {}).get("configurable") or {}).get("user_id") or "anonymous"


async def _backend_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.backend.base_url}/{path.lstrip('/')}"
    headers = {"X-API-Key": settings.backend.api_key} if settings.backend.api_key else {}
    client = await get_client()
    try:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        raise BackendUnavailable(str(exc)) from exc


async def get_saved_locations(config: RunnableConfig) -> str:
    """List the locations this user has saved, and which one is their default."""
    try:
        payload = await backend_get(f"/api/v1/users/{_user_id(config)}/locations")
        items = payload.get("locations") or []
        if not items:
            return (
                "This user has no saved locations. Offer to save one so future "
                "questions do not need a place name."
            )
        rows = [
            f"{item.get('label', 'unlabelled')}: {item.get('location')}"
            + (" (default)" if item.get("is_default") else "")
            for item in items
        ]
        return "Saved locations\n" + "\n".join(rows)
    except BackendUnavailable as exc:
        return fmt.tool_error("saved locations", str(exc))


async def save_location(
    config: RunnableConfig,
    location: str,
    label: str = "home",
    make_default: bool = False,
) -> str:
    """Save or update a location for this user, optionally as their default."""
    try:
        await _backend_post(
            f"/api/v1/users/{_user_id(config)}/locations",
            {"location": location, "label": label, "make_default": make_default},
        )
        suffix = " and set as the default location" if make_default else ""
        return f"Saved {location} under the label '{label}'{suffix}."
    except BackendUnavailable as exc:
        return fmt.tool_error("saving the location", str(exc))


async def manage_alert_subscription(
    config: RunnableConfig,
    district: str,
    subscribe: bool = True,
) -> str:
    """Subscribe or unsubscribe this user from push warnings for a district."""
    try:
        await _backend_post(
            f"/api/v1/users/{_user_id(config)}/subscriptions",
            {"district": district, "subscribe": subscribe},
        )
        if subscribe:
            return (
                f"Subscribed to IMD warnings for {district}. The user will get a push "
                "alert when a yellow warning or worse is issued."
            )
        return f"Unsubscribed from warnings for {district}."
    except BackendUnavailable as exc:
        return fmt.tool_error("the alert subscription", str(exc))


SAVED_LOCATIONS_TOOL = StructuredTool.from_function(
    coroutine=get_saved_locations,
    name="get_saved_locations",
    description=(
        "List the locations this user has saved and which is their default. Use when "
        "the user refers to 'my farm', 'my village' or 'my usual place'."
    ),
    args_schema=SavedLocationsInput,
)

SAVE_LOCATION_TOOL = StructuredTool.from_function(
    coroutine=save_location,
    name="save_location",
    description=(
        "Save or update a location for this user. Use when they say to remember a "
        "place or to change their default location."
    ),
    args_schema=SaveLocationInput,
)

SUBSCRIBE_ALERTS_TOOL = StructuredTool.from_function(
    coroutine=manage_alert_subscription,
    name="manage_alert_subscription",
    description=(
        "Turn push warning alerts on or off for a district for this user. Use when "
        "they ask to be notified, warned, or to stop receiving alerts."
    ),
    args_schema=SubscribeAlertsInput,
)

PROFILE_TOOLS = [SAVED_LOCATIONS_TOOL, SAVE_LOCATION_TOOL, SUBSCRIBE_ALERTS_TOOL]
