import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Isolate test runs from the development database (env vars override .env)
os.environ["DATABASE_URL"] = "sqlite:///./test_weathergpt.db"

# ASGITransport skips FastAPI lifespan, so ensure the alerts schema exists
# before any test touches the alert endpoints.
from src.alerts.database import init_db as init_alerts_db

init_alerts_db()
