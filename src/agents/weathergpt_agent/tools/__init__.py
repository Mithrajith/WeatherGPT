"""Tool registry.

All eight tools go to the agent on every turn and the model picks. There is no
intent router and no per-intent subset: choosing a tool is what the tool-calling
loop is for, and the tool descriptions in `weather.py` / `profile.py` are where
that choice is steered.

If the tool count ever grows past what fits comfortably in a prompt, the answer
is LangChain's tool-selection middleware (progressive tool disclosure), not a
hand-written router.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from .profile import (
    PROFILE_TOOLS,
    SAVE_LOCATION_TOOL,
    SAVED_LOCATIONS_TOOL,
    SUBSCRIBE_ALERTS_TOOL,
)
from .weather import (
    CURRENT_WEATHER_TOOL,
    FARM_ADVISORY_TOOL,
    FORECAST_TOOL,
    HISTORICAL_TREND_TOOL,
    WARNINGS_TOOL,
    WEATHER_TOOLS,
)

ALL_TOOLS: list[BaseTool] = [*WEATHER_TOOLS, *PROFILE_TOOLS]

TOOLS_BY_NAME: dict[str, BaseTool] = {tool.name: tool for tool in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "TOOLS_BY_NAME",
    "WEATHER_TOOLS",
    "PROFILE_TOOLS",
    "CURRENT_WEATHER_TOOL",
    "FORECAST_TOOL",
    "WARNINGS_TOOL",
    "FARM_ADVISORY_TOOL",
    "HISTORICAL_TREND_TOOL",
    "SAVED_LOCATIONS_TOOL",
    "SAVE_LOCATION_TOOL",
    "SUBSCRIBE_ALERTS_TOOL",
]
