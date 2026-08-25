"""Local REPL for the agent, so the agent layer can be exercised before the
frontend or the voice layer exist.

    python -m weather_gpt                          # interactive chat
    python -m weather_gpt --persona farmer
    python -m weather_gpt --ask "rain in Nashik tomorrow"
    python -m weather_gpt --stream                  # token streaming
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from .agent import META_KEY, WeatherGPTAgent, message_text
from .config import get_settings


def _trace(reply) -> str:
    meta = (reply.response_metadata or {}).get(META_KEY, {})
    return (
        f"     [tools={meta.get('tools_used') or '-'} "
        f"degraded={meta.get('degraded')} {meta.get('latency_ms')}ms]"
    )


async def _chat(args: argparse.Namespace) -> None:
    agent = WeatherGPTAgent()
    session_id = str(uuid.uuid4())
    kwargs = {
        "session_id": session_id,
        "user_id": args.user_id,
        "language": args.language,
        "location": args.location,
        "persona": args.persona,
    }

    try:
        if args.ask:
            reply = await agent.achat(args.ask, **kwargs)
            print(f"\n{message_text(reply)}\n")
            print(_trace(reply))
            return

        print("WeatherGPT. Type 'quit' to exit.\n")
        while True:
            text = input("you> ").strip()
            if text.lower() in {"quit", "exit", "q"}:
                break
            if not text:
                continue

            if args.stream:
                print("bot> ", end="", flush=True)
                async for token in agent.astream(text, **kwargs):
                    print(token, end="", flush=True)
                print("\n")
            else:
                reply = await agent.achat(text, **kwargs)
                print(f"bot> {message_text(reply)}")
                print(f"{_trace(reply)}\n")
    finally:
        await agent.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="weather_gpt", description="WeatherGPT agent CLI")
    parser.add_argument("--ask", help="single question, then exit")
    parser.add_argument("--persona", choices=["farmer", "general"], default="general")
    parser.add_argument("--language", default="en", help="language of the input")
    parser.add_argument("--location", default=None, help="default location context")
    parser.add_argument("--user-id", default="cli-user")
    parser.add_argument("--stream", action="store_true", help="stream tokens")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if (args.verbose or get_settings().debug) else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(_chat(args))
    except (KeyboardInterrupt, EOFError):
        print("\nbye")


if __name__ == "__main__":
    main()
