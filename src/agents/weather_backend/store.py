"""User state: saved locations and alert subscriptions.

SQLite via the standard library. The architecture calls for Postgres, and the
schema and queries here are plain enough to port when the shared database exists;
what matters for the agent is that writes survive a restart and one user's rows
are never visible to another.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Any

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    user_id    TEXT NOT NULL,
    label      TEXT NOT NULL,
    location   TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, label)
);
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id  TEXT NOT NULL,
    district TEXT NOT NULL,
    PRIMARY KEY (user_id, district)
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def list_locations(user_id: str) -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT label, location, is_default FROM locations WHERE user_id = ? "
            "ORDER BY is_default DESC, label",
            (user_id,),
        ).fetchall()
    return [
        {"label": r["label"], "location": r["location"], "is_default": bool(r["is_default"])}
        for r in rows
    ]


def save_location(user_id: str, location: str, label: str, make_default: bool) -> None:
    with closing(_connect()) as conn:
        if make_default:
            conn.execute("UPDATE locations SET is_default = 0 WHERE user_id = ?", (user_id,))
        conn.execute(
            "INSERT INTO locations (user_id, label, location, is_default) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, label) DO UPDATE SET location = excluded.location, "
            "is_default = excluded.is_default",
            (user_id, label, location, int(make_default)),
        )
        conn.commit()


def set_subscription(user_id: str, district: str, subscribe: bool) -> list[str]:
    with closing(_connect()) as conn:
        if subscribe:
            conn.execute(
                "INSERT OR IGNORE INTO subscriptions (user_id, district) VALUES (?, ?)",
                (user_id, district),
            )
        else:
            conn.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND district = ?",
                (user_id, district),
            )
        conn.commit()
        rows = conn.execute(
            "SELECT district FROM subscriptions WHERE user_id = ? ORDER BY district",
            (user_id,),
        ).fetchall()
    return [r["district"] for r in rows]


def all_subscriptions() -> list[dict[str, str]]:
    """Every watch, for the alerts lead's polling job."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT user_id, district FROM subscriptions ORDER BY district"
        ).fetchall()
    return [{"user_id": r["user_id"], "district": r["district"]} for r in rows]
