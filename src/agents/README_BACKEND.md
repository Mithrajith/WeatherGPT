# WeatherGPT backend service

Implements the contract the agent's tools call. Two data tiers, chosen per request:

| Tier | Needs a key | Used for |
|---|---|---|
| **IMD** (`api.imd.gov.in`) | yes | authoritative observations, city forecasts, official district warnings |
| **Open-Meteo + ERA5** | no | live observations, forecasts, real climate normals, and derived hazard/agromet products |

Without a key the service still returns **real live data** — it does not fall back to
canned values. What it cannot do is issue an *official* warning, so anything it derives
itself is labelled `official: false`, and the agent is required to say so.

## Run it

```powershell
uv sync --extra backend
uv run --extra backend uvicorn weather_backend.main:app --port 8000
```

Health check, which also tells you which tier is active:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

## Endpoints

```
GET  /api/v1/weather/current    ?location= | ?lat=&lon=
GET  /api/v1/weather/forecast   ?location=&days=1..7
GET  /api/v1/warnings/district  ?district=&severity_floor=green|yellow|orange|red
GET  /api/v1/advisory/agromet   ?location=&crop=&activity=&days=
GET  /api/v1/climate/trend      ?district=&month=1..12&metric=rainfall|temperature&years=
GET  /api/v1/users/{id}/locations
POST /api/v1/users/{id}/locations       {location,label,make_default}
POST /api/v1/users/{id}/subscriptions   {district,subscribe}
GET  /api/v1/health
```

Every weather response carries a `source` string. Hazard and advisory responses also
carry `official: true|false`.

## Where each number comes from

- **Current / forecast** — IMD `current_wx` and `cityforecast` when keyed. IMD publishes
  daily min/max and worded forecasts but *not* rainfall amounts, so with a key the
  service overlays IMD temperatures and wording on Open-Meteo rainfall and says exactly
  that in `source`. Mixing them silently would let the agent credit IMD for numbers IMD
  never issued.
- **Warnings** — IMD `districtwarning` when keyed (`official: true`). Otherwise the live
  forecast is scored against IMD's published 24-hour thresholds — heavy 64.5–115.5 mm,
  very heavy 115.6–204.4 mm, extremely heavy ≥204.5 mm, plus wind and heat bands — and
  returned as `official: false`.
- **Agromet** — derived from the forecast with documented agronomic rules (spray/irrigation
  /harvest decisions keyed off rainfall and wind). IMD's real agromet bulletins need a key.
- **Climate trend** — ERA5 reanalysis via the Open-Meteo archive, aggregated per month
  across N years. This is genuine climatology, not a canned normal. ERA5 lags ~5 days, so
  an in-progress month is flagged as partial.
- **User state** — SQLite (`BACKEND_DB`). Port to the shared Postgres when it exists; the
  queries in `store.py` are plain enough to move as-is.

## Getting an IMD API key

The gateway rejects every unauthenticated call with `{"error":"API key missing"}`, so the
IMD tier is off until you have one. Two routes:

**1. IMD directly (the authoritative data, and what the endpoints above are written for)**

- Reference of all 20 endpoints: <https://api.imd.gov.in/public/api_reference.html>
- Portal: <https://api.imd.gov.in/> — "IMD API Management Platform", run by the ISSD team,
  DGM Office.
- IMD's API document lists a contact for access requests:
  <https://mausam.imd.gov.in/Forecast/marquee_data/API_doc.pdf> — the contact given there
  is **sankar.nath@imd.gov.in**. Request API access for a named project, state the
  endpoints you need (`cityforecast`, `current_wx`, `districtwarning`, `districtnowcast`,
  `districtrainfall`), and mention it is for a hackathon prototype.
- Data supply is also handled through IMD's data supply procedure
  (<https://mausam.imd.gov.in/newdelhi/docs/data-procedure.pdf>) if the API route is slow.

Once you have it:

```
IMD_API_KEY=<your key>
```

Then restart the service and check `/api/v1/health` shows `"imd_tier": "enabled"`. If IMD
calls still fail, the key is probably expected in a differently named header — set
`IMD_KEY_HEADER` to whatever the gateway documents for your account. The service sends the
key both as that header and as an `api_key` query parameter, and falls back to Open-Meteo
on any IMD failure, so a wrong guess degrades instead of breaking.

**2. data.gov.in (self-service, instant, but historical datasets rather than live feeds)**

Register at <https://www.data.gov.in/> and copy the API key from your account page, then
use it against IMD datasets published there. Useful for rainfall archives; not a
substitute for live nowcasts and warnings.

## Caveat on the IMD code paths

The IMD request/parse code in `sources.py` is written from the published field reference
but has **never executed against the live gateway**, because no key was available. It is
structured so that any IMD failure raises and the request falls back to the public tier.
Expect to adjust field names on first contact with a real response — and check
`/api/v1/health` plus one `?location=` call per endpoint before trusting it.
