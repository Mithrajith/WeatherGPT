"""End-to-end smoke run for the agent layer.

Exercises each path a judge is likely to touch, against the fake backend and a
local model, in one process so the model loads once.

    uv run --extra backend uvicorn weather_backend.main:app --port 8000      # in another terminal
    uv run python scripts/smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from weathergpt_agent import META_KEY, WeatherGPTAgent, message_text  # noqa: E402

CASES: list[tuple[str, dict]] = [
    (
        "forecast",
        {"message": "will it rain in Coimbatore tomorrow", "location": "Coimbatore"},
    ),
    (
        "follow-up (same session, tests memory)",
        {"message": "and the day after?", "location": "Coimbatore"},
    ),
    (
        "hazard / safety",
        {"message": "is it safe to travel in Thanjavur tonight", "location": "Thanjavur"},
    ),
    (
        "farm advisory",
        {
            "message": "should I spray my cotton this week",
            "location": "Nashik",
            "persona": "farmer",
        },
    ),
    (
        "profile write (config-injected user_id)",
        {"message": "remember my farm is in Erode and alert me about warnings there"},
    ),
    (
        "profile read (tool with no arguments)",
        {"message": "which locations have you saved for me?"},
    ),
    ("smalltalk (should call no tools)", {"message": "hello, what can you do?"}),
    (
        "historical",
        {"message": "was August drier than usual in Pune?", "location": "Pune"},
    ),
]


async def main() -> None:
    agent = WeatherGPTAgent()
    session = "smoke-session"
    failures = 0

    try:
        for label, kwargs in CASES:
            kwargs.setdefault("persona", "general")
            reply = await agent.achat(session_id=session, user_id="smoke-user", **kwargs)
            meta = (reply.response_metadata or {}).get(META_KEY, {})
            text = message_text(reply)

            print("=" * 78)
            print(f"CASE  {label}")
            print(f"ASK   {kwargs['message']}")
            print(f"REPLY {text}")
            print(
                f"META  tools={meta.get('tools_used')} degraded={meta.get('degraded')} "
                f"latency={meta.get('latency_ms')}ms error={meta.get('error')}"
            )
            if meta.get("error"):
                failures += 1
            if not text:
                failures += 1
    finally:
        await agent.aclose()

    print("=" * 78)
    print(f"cases: {len(CASES)}  failures: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
