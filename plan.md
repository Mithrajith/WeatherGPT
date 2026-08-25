# WeatherGPT — 2-Day MVP Build Plan (6-Member Team)

## 0. Reality check first

The brief lists GFS/WRF model integration, MQTT/WIS2.0 ingestion, full GIS tooling, Kubernetes, and coverage of agriculture + aviation + marine + urban use cases. None of that is buildable from scratch in 48 hours. Running WRF alone takes a HPC cluster and days of compute. The winning move in a 2-day hackathon is never "build everything shallow" — it's "make one path genuinely work end-to-end, and show the rest as a credible architecture diagram."

So the plan below is split into:
- **P0 (must demo, built for real):** conversational weather Q&A, one real-time IMD data source, one alert type, one Indian language with voice, one persona (recommend **farmer/agriculture advisory** — it's the most demo-friendly and matches "disaster preparedness" and "rural accessibility" judging criteria in one shot).
- **P1 (nice to have if time allows):** climate trend mini-chart, second language, cyclone/flood alert push.
- **P2 (architecture-diagram only, don't build):** GFS/WRF raw NWP ingestion, WIS2.0/MQTT pipeline, Kubernetes, full GIS layer, aviation/marine advisories. Put these in your pitch deck as "Phase 2 roadmap" — judges reward knowing what to defer, not just what to build.

## 1. Real data sources you can actually use in 2 days

**India Meteorological Department (IMD) open APIs** — `api.imd.gov.in` and `mausam.imd.gov.in` — are the backbone. They already expose processed, ready-to-consume JSON for: <cite index="18-1">7-day city weather forecast (by name or lat/long), subdivision and district rainfall forecasts, current weather (Mausamgram), district/subdivision-wise nowcasts and warnings, AWS/ARG station data, river-basin QPF, cyclone track and cone-of-uncertainty, fishermen and coastal/port warnings, highway nowcast warnings, and agromet advisories</cite>. This is exactly the "real-time meteorological system integration" the evaluators want, and you don't have to touch raw NWP grids to get it — IMD has already run GFS/WRF-class models upstream and handed you the output.

Use this as your **only** live data source for the demo. Don't also wire up NOAA/Open-Meteo/OpenWeatherMap unless IMD is flaky on the day — keep one global API (Open-Meteo, no key needed) as a silent fallback, not a second feature to build.

**Multilingual + voice**: Bhashini (bhashini.gov.in), the Government of India's language platform, is the right call here specifically because the brief asks for Indian-language support — <cite index="19-1">it's free for all Indian citizens and provides APIs for developers, covering text-to-speech, real-time translation, and speech-to-text across 22 Indian languages</cite>. It's built by MeitY with IIT/CDAC research groups, exposed through a model-registry called ULCA where you pick a model ID per language/task and call a pipeline endpoint — <cite index="24-1">the R&D groups from IITB, IITM, IIITH, CDAC etc. have built the underlying speech recognition, translation, and text-to-speech models, exposed via the ULCA platform</cite>. Budget real setup time for this (account creation, model-ID lookup, auth) — it's the one external dependency that can eat your first evening if you leave it late.

**LLM for the agent core**: pick for latency and function-calling reliability, not raw benchmark score — judges see latency directly. As of August 2026, the standing free-tier field looks like this: Google's Gemini Flash models remain free with no card required, Groq gives fast free inference (30 req/min on a strong open model) purpose-built for real-time chat, and Cerebras offers high daily free volume too. Recommendation: **Groq (Llama or GPT-OSS) as primary for low-latency responses, Gemini Flash as fallback/for anything needing longer context** (e.g. summarizing a multi-day forecast bulletin). Both are OpenAI-tool-calling compatible, which matters for the agent architecture below.

## 2. Architecture

```
User (chat text / voice, EN or Indian language)
        │
        ▼
Bhashini STT + translate-to-English  (voice/language layer)
        │
        ▼
FastAPI gateway ──► LangGraph agent (query router)
        │                    │
        │        ┌───────────┴────────────┐
        │        ▼                        ▼
        │   Tool: IMD live APIs      Tool: Postgres (structured:
        │   (forecast/nowcast/       user locations, saved queries,
        │    warnings/agromet)       alert subscriptions)
        │        │                        │
        │        └───────────┬────────────┘
        │                    ▼
        │           LLM composes answer (Groq / Gemini Flash)
        │                    │
        ▼                    ▼
Bhashini translate-back + TTS   WebSocket push (for proactive alerts)
        │
        ▼
Mobile-first PWA (React) — chat UI + alert banner + simple map
```

This is the same **query-routing-between-a-structured-store-and-real-time-source** pattern from your Vizset RAG work — there you routed between Postgres and a vector store behind FastAPI; here you're routing between Postgres (user/session state) and live IMD endpoints (weather facts), with the LLM deciding which tool(s) a query needs. You can port that routing logic almost directly, which is the single biggest time-saver available to you — **you should own the agent orchestration piece**, since it's the part you've already built once.

Skip a vector store for v1. If you want the "climate trend analysis" checkbox cheaply, don't build RAG over a corpus — just have IMD's historical/rainfall-by-district data sit in a small Postgres table and let the LLM call a `get_historical_trend(district, month)` tool that does a SQL aggregation. Looks the same to a judge, costs a fraction of the time.

## 3. Team split (6 people)

| # | Role | Owns |
|---|------|------|
| 1 | **Agent/LLM lead** (you) | LangGraph router, tool schemas, prompt design, Groq/Gemini integration, latency tuning |
| 2 | **Backend/API lead** | FastAPI service, IMD API wrappers + response caching, Postgres schema (users, locations, subscriptions, historical table) |
| 3 | **Multilingual/Voice lead** | Bhashini account + ULCA model IDs, STT/TTS pipeline, language switch UX, fallback to browser Web Speech API if Bhashini latency is bad on demo wifi |
| 4 | **Alerts/Advisory lead** | District warning polling job → WebSocket push, farmer advisory tool (crop + weather rule logic), demo alert scenario (e.g. simulate a cyclone/heavy-rain warning) |
| 5 | **Frontend lead** | Mobile-first PWA: chat interface, voice mic button, alert banner, one simple map view (Leaflet, just markers/district highlight — not full GIS) |
| 6 | **DevOps + Integration/Pitch lead** | Docker Compose, env/secrets management, deployed demo URL (Render/Railway/HF Spaces), end-to-end test pass, pitch deck + backup demo video, judge Q&A prep on the P2 roadmap items |

Keep roles 2–5 building against a shared OpenAPI contract you all agree on in hour 1, so nobody blocks on nobody.

## 4. Hour-by-hour timeline (48h)

**Kickoff (before hour 0):** lock scope to the P0 list above, split roles, everyone gets accounts provisioned same night — IMD API access, Bhashini developer account, Groq + Gemini API keys, GitHub repo + Docker Compose skeleton. This alone saves 3–4 hours on day 1.

**Day 1**
- **0–4h:** Repo/skeleton up. Backend lead confirms real IMD endpoint responses (their docs drift — verify actual JSON shape, not just the reference page). Agent lead scaffolds LangGraph with 2 dummy tools. Voice lead completes Bhashini auth + one working STT call. Frontend scaffolds chat UI shell.
- **4–12h:** Backend wraps 3 IMD tools (current weather, 7-day forecast, district warnings) with caching. Agent lead wires them into LangGraph with real tool-calling. Frontend builds working chat loop against a mocked backend response, then swaps to real API.
- **12–16h:** **Checkpoint: text-only English Q&A must work end-to-end** (ask "will it rain in Coimbatore tomorrow" → real IMD-backed answer). This is your floor — don't move on until this works.
- **16–20h:** Voice lead adds TTS + translate-back. Alerts lead builds the warning-polling job and WebSocket push. Agromet/farmer advisory tool added.
- **20–24h:** Integrate voice into the chat UI end-to-end in Hindi or Tamil (pick one language, do it well). Sleep rotation — don't run all 6 people to zero at once.

**Day 2**
- **24–32h:** Second language if time allows (P1). Alert banner UI + simulated warning scenario rehearsed. Historical-trend tool + tiny chart in UI (P1).
- **32–40h:** Dockerize everything, deploy to a public URL. Fix whatever breaks in a clean container (always something). Latency pass — cache IMD responses, trim prompt size, confirm Groq path is actually the fast path in practice.
- **40–44h:** Full run-throughs of the demo script, including the voice-in-rural-language moment and the disaster-alert push — these are your two highest-scoring moments against the evaluation criteria. Fix edge cases (no internet fallback message, unknown location handling).
- **44–48h:** Pitch deck (problem → architecture diagram incl. P2 roadmap → live demo → evaluation-criteria mapping), record a backup demo video in case live wifi fails, final polish, submit.

## 5. Mapping to evaluation criteria

- **Accuracy/relevance & real-time integration** → live IMD API calls, not static data.
- **Response latency** → Groq as primary inference path; cache IMD responses (weather doesn't change every second).
- **Multilingual capability** → Bhashini, one language done well beats three done badly.
- **UI/accessibility** → voice-first framing in the demo, not just a feature buried in a menu.
- **Scalability/innovation** → the architecture diagram showing WIS2.0/MQTT/Kubernetes/multi-NWP as Phase 2, plus the agent's tool-routing design as the "innovation" story.
- **Disaster preparedness** → the simulated warning → push-alert demo moment.

Good luck — happy to help draft the actual FastAPI tool schemas, the LangGraph router, or the pitch deck once you're ready to start writing code.