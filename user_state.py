# -*- coding: utf-8 -*-
"""
Хранилище прогресса пользователя по тесту (в памяти процесса).
"""

# user_id -> {"index": int, "score": int}
_progress: dict[int, dict] = {}


def start_quiz(user_id: int):
    _progress[user_id] = {"index": 0, "score": 0}


def get_current_index(user_id: int) -> int:
    return _progress.get(user_id, {}).get("index", 0)


def advance(user_id: int):
    state = _progress.setdefault(user_id, {"index": 0, "score": 0})
    state["index"] += 1


def register_answer(user_id: int, is_correct: bool):
    state = _progress.setdefault(user_id, {"index": 0, "score": 0})
    if is_correct:
        state["score"] += 1


def get_score(user_id: int) -> int:
    return _progress.get(user_id, {}).get("score", 0)


def clear(user_id: int):
    _progress.pop(user_id, None)
