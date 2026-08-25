"""WeatherGPT agent layer.

The LangChain/LangGraph half of the system: tools, prompt design and provider
management, on top of LangChain's prebuilt `create_agent` harness. Weather data
comes from the FastAPI service (IMD wrappers + Postgres) over the shared OpenAPI
contract.

Gateway usage:

    from weathergpt_agent import WeatherGPTAgent, message_text

    agent = WeatherGPTAgent()              # once, at app startup
    reply = await agent.achat("will it rain in Coimbatore tomorrow",
                              session_id=sid, persona="farmer")
    message_text(reply)                    # answer text
    reply.model_dump()                     # JSON for the API response
"""

from .agent import (
    META_KEY,
    WeatherGPTAgent,
    get_primary_model,
    message_text,
    tools_used,
    was_degraded,
)
from .alerts import compose_alert
from .config import get_settings

__version__ = "0.3.0"

__all__ = [
    "WeatherGPTAgent",
    "META_KEY",
    "compose_alert",
    "get_primary_model",
    "get_settings",
    "message_text",
    "tools_used",
    "was_degraded",
    "__version__",
]
