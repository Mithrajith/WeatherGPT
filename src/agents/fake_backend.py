"""Stand-in for the backend lead's FastAPI service, for local agent development.

Serves the shape agreed in the OpenAPI contract with canned IMD-like data, so the
agent layer can be exercised end to end before the real service exists. Standard
library only, no dependencies.

    uv run python scripts/fake_backend.py --port 8000

Query it with ?empty=1 on any path to get a not_found response, or start it with
--fail to make every endpoint return 503, which is how the Open-Meteo fallback
and the TOOL_ERROR paths get tested.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FAIL_MODE = False

_SAVED: dict[str, list[dict]] = {}
_SUBSCRIPTIONS: dict[str, list[str]] = {}


def _days(n: int) -> list[dict]:
    today = date.today()
    rows = []
    for i in range(n):
        rows.append(
            {
                "date": (today + timedelta(days=i)).isoformat(),
                "temp_min": 24 + i,
                "temp_max": 33 + (i % 3),
                "rainfall": [0.0, 12.5, 40.0, 5.0, 0.0, 2.0, 18.0][i % 7],
                "rain_chance": [10, 60, 90, 35, 5, 20, 70][i % 7],
                "condition": [
                    "partly cloudy",
                    "rain showers",
                    "heavy rain",
                    "light rain",
                    "clear sky",
                    "partly cloudy",
                    "thunderstorm",
                ][i % 7],
            }
        )
    return rows


def _payload(path: str, params: dict[str, list[str]]) -> tuple[int, dict]:
    if params.get("empty"):
        return 200, {"status": "not_found", "detail": "no record for this location"}

    place = (params.get("location") or params.get("district") or ["Coimbatore"])[0]

    if path.endswith("/weather/current"):
        return 200, {
            "current": {
                "observed_at": "today 14:30 IST",
                "condition": "partly cloudy",
                "temperature": 32.4,
                "feels_like": 36.1,
                "humidity": 68,
                "precipitation": 0.0,
                "wind_speed": 14.0,
                "station": f"{place} AWS",
            }
        }

    if path.endswith("/weather/forecast"):
        try:
            count = max(1, min(int((params.get("days") or ["3"])[0]), 7))
        except ValueError:
            count = 3
        return 200, {"forecast": _days(count)}

    if path.endswith("/warnings/district"):
        return 200, {
            "warnings": [
                {
                    "severity": "orange",
                    "hazard": "heavy rainfall",
                    "district": place,
                    "valid_from": "today 18:00 IST",
                    "valid_until": "tomorrow 08:00 IST",
                    "description": (
                        "Heavy to very heavy rain likely at isolated places, "
                        "70 to 110 millimetres in 24 hours."
                    ),
                }
            ]
        }

    if path.endswith("/advisory/agromet"):
        crop = (params.get("crop") or ["other"])[0]
        return 200, {
            "advisory": {
                "driver": "heavy rain expected in the next 48 hours",
                "recommendation": (
                    f"Postpone spraying on {crop}. Drain excess water from field "
                    "channels and move harvested produce under cover."
                ),
                "window": "resume field operations after Thursday morning",
                "risk": "lodging and fungal infection if rain persists",
                "issued_by": "IMD agromet, district advisory bulletin",
            },
            "forecast_summary": "40 millimetres tomorrow, 5 millimetres on Thursday",
        }

    if path.endswith("/climate/trend"):
        return 200, {
            "trend": {
                "period": "August, 10-year mean",
                "years": 10,
                "normal": 118.4,
                "latest": 86.2,
                "anomaly": -32.2,
                "percent_of_normal": 73,
                "direction": "drier than normal",
            }
        }

    if "/locations" in path:
        user = path.split("/users/")[1].split("/")[0]
        return 200, {"locations": _SAVED.get(user, [])}

    return 404, {"status": "not_found", "detail": f"unhandled path {path}"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if FAIL_MODE:
            return self._send(503, {"detail": "simulated backend outage"})
        parsed = urlparse(self.path)
        status, body = _payload(parsed.path, parse_qs(parsed.query))
        self._send(status, body)

    def do_POST(self) -> None:  # noqa: N802
        if FAIL_MODE:
            return self._send(503, {"detail": "simulated backend outage"})
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        parsed = urlparse(self.path)
        user = parsed.path.split("/users/")[1].split("/")[0] if "/users/" in parsed.path else "?"

        if parsed.path.endswith("/locations"):
            _SAVED.setdefault(user, []).append(
                {
                    "label": body.get("label", "home"),
                    "location": body.get("location"),
                    "is_default": bool(body.get("make_default")),
                }
            )
            return self._send(200, {"status": "saved"})

        if parsed.path.endswith("/subscriptions"):
            district = body.get("district", "")
            watched = _SUBSCRIPTIONS.setdefault(user, [])
            if body.get("subscribe", True):
                watched.append(district)
            elif district in watched:
                watched.remove(district)
            return self._send(200, {"status": "ok", "districts": watched})

        self._send(404, {"status": "not_found"})

    def log_message(self, fmt: str, *args) -> None:
        print("backend:", fmt % args, flush=True)


def main() -> None:
    global FAIL_MODE
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--fail", action="store_true", help="return 503 for everything")
    args = parser.parse_args()
    FAIL_MODE = args.fail

    print(f"fake IMD backend on http://127.0.0.1:{args.port} (fail_mode={FAIL_MODE})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
