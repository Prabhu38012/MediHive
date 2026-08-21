"""
memory/shared_memory.py

Phase 4: Append-only shared memory. Every agent response (including
debate revisions) is written here. Any agent or the debate/fusion layer
can read the full history for a given question.

SQLite chosen over Redis/in-memory dict deliberately:
- Persists across restarts (useful for demos / grading review)
- Zero infra setup (single file, no server)
- Easy to inspect directly for the project report (`sqlite3 memory.db`)
"""

import sqlite3
import os
import json
from contextlib import contextmanager

DB_PATH = os.getenv("SHARED_MEMORY_DB_PATH", "./data/memory.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)


@contextmanager
def _connection():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round INTEGER NOT NULL DEFAULT 0,
                agent TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def save_response(session_id: str, round_num: int, response) -> None:
    """response: an AgentResponse (pydantic model) from base_agent.py"""
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_responses
                (session_id, round, agent, question, answer, reasoning, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                round_num,
                response.agent,
                response.question,
                response.answer,
                response.reasoning,
                response.confidence,
                response.timestamp,
            ),
        )


def get_session_history(session_id: str) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_responses WHERE session_id = ? ORDER BY round, id",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_latest_round(session_id: str) -> list[dict]:
    """Return only the most recent round's responses (used to feed the
    debate engine the current state without re-reading old rounds)."""
    history = get_session_history(session_id)
    if not history:
        return []
    max_round = max(r["round"] for r in history)
    return [r for r in history if r["round"] == max_round]


def dump_session_json(session_id: str) -> str:
    """Convenience for demos: pretty-print a full session's memory."""
    return json.dumps(get_session_history(session_id), indent=2)
