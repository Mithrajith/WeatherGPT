"""Proactive alert composition.

The alerts lead owns the polling job and the WebSocket push. This module is the
agent-layer half: turning an IMD warning payload into one short, speakable
sentence that survives translation and reads well in a push banner.

Deliberately a single LLM call with no tools. A push alert must be fast and must
never depend on a tool-calling loop that could stall; if the LLM is unavailable
we fall back to a deterministic template, because a slightly clunky alert that
arrives beats an elegant one that does not.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .agent import get_primary_model

logger = logging.getLogger(__name__)

ALERT_SYSTEM_PROMPT = """You write push notifications for official IMD weather warnings.

Output one or two sentences, at most 40 words total, and nothing else. No greeting, \
no sign-off, no markdown, no emoji.

Always write in English, whatever language the recipient reads. Translation happens \
downstream in the Bhashini layer; an alert already in Tamil would be translated twice.

Structure: the hazard and its severity colour, the district, the time window, then the \
single most important protective action.

Never soften or downgrade an official warning. Never add a hazard the payload does not \
contain. Write it to be read aloud, and keep the wording simple enough to translate \
cleanly into an Indian language.

If the persona is 'farmer', make the action agricultural, for example moving harvested \
produce under cover or delaying a spray."""

SEVERITY_ACTION = {
    "red": "Take shelter now and follow local authority instructions.",
    "orange": "Avoid travel and move livestock and harvested produce to shelter.",
    "yellow": "Stay alert and delay outdoor field work.",
    "green": "No action needed. Conditions are normal.",
}


def _template_alert(warning: dict[str, Any]) -> str:
    """Deterministic fallback. Used when the LLM call fails."""
    severity = str(warning.get("severity") or warning.get("colour") or "yellow").lower()
    hazard = warning.get("hazard") or warning.get("type") or "severe weather"
    district = warning.get("district") or "your district"
    window = warning.get("valid_until")
    when = f" until {window}" if window else ""
    action = SEVERITY_ACTION.get(severity, SEVERITY_ACTION["yellow"])
    return f"IMD {severity} warning: {hazard} in {district}{when}. {action}"


async def compose_alert(
    warning: dict[str, Any], persona: str = "general", language: str = "en"
) -> str:
    """Turn one IMD warning record into a push-ready sentence.

    Returns English. The Bhashini layer translates and voices it downstream;
    `language` is passed only so the model keeps the phrasing translation-safe.
    """
    payload = "\n".join(
        f"{key}: {value}" for key, value in warning.items() if value not in (None, "")
    )
    prompt = (
        f"Persona: {persona}\nTarget language after translation: {language}\n\n"
        f"IMD warning record:\n{payload}"
    )

    try:
        model = get_primary_model()
        response = await model.ainvoke(
            [SystemMessage(content=ALERT_SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
        text = response.content if isinstance(response.content, str) else ""
        text = text.strip()
        if text:
            return text
        logger.warning("empty alert composition, using template")
    except Exception as exc:  # noqa: BLE001
        logger.warning("alert composition failed, using template: %s", exc)

    return _template_alert(warning)


__all__ = ["compose_alert", "ALERT_SYSTEM_PROMPT"]
