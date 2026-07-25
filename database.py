# -*- coding: utf-8 -*-
import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH

EVENT_BOT_OPENED = "bot_opened"
EVENT_QUIZ_STARTED = "quiz_started"
EVENT_QUIZ_COMPLETED = "quiz_completed"
EVENT_GROUP_CLICKED = "group_clicked"
EVENT_PODCAST_CLICKED = "podcast_clicked"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                ts INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)")


def log_event(user_id: int, event: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO events (user_id, event, ts) VALUES (?, ?, ?)",
            (user_id, event, int(time.time())),
        )


def _distinct(event: str, conn) -> int:
    cur = conn.execute(
        "SELECT COUNT(DISTINCT user_id) FROM events WHERE event = ?", (event,)
    )
    return cur.fetchone()[0]


def get_stats() -> dict:
    with get_conn() as conn:
        return {
            "opened":          _distinct(EVENT_BOT_OPENED, conn),
            "started":         _distinct(EVENT_QUIZ_STARTED, conn),
            "completed":       _distinct(EVENT_QUIZ_COMPLETED, conn),
            "group_clicks":    _distinct(EVENT_GROUP_CLICKED, conn),
            "podcast_clicks":  _distinct(EVENT_PODCAST_CLICKED, conn),
        }


def get_completed_users() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM events WHERE event = ?",
            (EVENT_QUIZ_COMPLETED,)
        ).fetchall()
        return [r[0] for r in rows]
