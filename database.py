import sqlite3
from datetime import datetime

DB_PATH = "analytics.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def log_event(user_id: int, event: str):
    """
    События:
      start          — открыл бота (/start)
      not_subscribed — так и не прошёл проверку подписки
      test_started   — начал тест
      test_finished  — прошёл до конца
      btn_individual — нажал «Записаться на разбор»
      btn_group      — нажал «Лист ожидания группы»
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO events (user_id, event, created_at) VALUES (?, ?, ?)",
            (user_id, event, datetime.now().isoformat())
        )
        conn.commit()


def get_stats() -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        def count_unique(event):
            row = conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM events WHERE event = ?",
                (event,)
            ).fetchone()
            return row[0] if row else 0

        return {
            "start":          count_unique("start"),
            "not_subscribed": count_unique("not_subscribed"),
            "test_started":   count_unique("test_started"),
            "test_finished":  count_unique("test_finished"),
            "btn_individual": count_unique("btn_individual"),
            "btn_group":      count_unique("btn_group"),
        }
