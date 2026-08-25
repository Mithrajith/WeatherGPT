"""weather_gpt package.

`main.py` (the old standalone FastAPI app, with its fabricated IMD fallback)
is no longer the project's entrypoint -- see `gateway.main` -- so it is not
imported eagerly here. Submodules like `voice_service` and
`llm_service` have no such dependency and can be imported directly, e.g.
`from weather_gpt.voice_service import VoiceService`.
"""
