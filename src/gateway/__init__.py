"""Integration gateway: the single FastAPI entrypoint for the whole project.

Wires together the five components built by the team:

- `weather_backend` (agent lead's honest IMD -> Open-Meteo backend) mounted at
  `/backend`, so the agent's tools (which default to `WEATHER_BACKEND_URL=
  http://localhost:8000`) keep working unchanged when this gateway also runs
  on port 8000.
- `weathergpt_agent` (LangGraph/LangChain agent) driving `/api/chat` and
  `/api/chat/voice`, the endpoints the frontend already calls.
- `src.alerts` (alert/advisory router + WebSocket push), mounted at root so
  `/alerts/{district}`, `/advisory` and `/ws/alerts` keep their existing paths.
  `/api/v1/alerts/active` is added as a thin alias over the same alert store,
  matching what the frontend calls.
- `src.multilingual_system` (MultilingualSystem) translating chat text at the
  gateway boundary, so the agent itself only ever sees English.
- `weather_gpt.voice_service` (VoiceService) for STT/TTS behind
  `/api/chat/voice`.

`src.weather_gpt.main:app` (the old tracked entrypoint, with its fabricated
IMD fallback) is intentionally not used here; `weather_backend` replaced it as
the canonical weather-data source.
"""
