"""Token & cost tracking for agent sessions.

Tracks input/output token usage per session for observability.
Data is stored in-memory and logged to the agent_memory DB.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("data/agent_memory")
COST_DB = str(MEMORY_DIR / "cost_tracker.db")

ESTIMATED_RATES = {
    "gpt-oss-120b": {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
    "gemini-2.5-flash": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "mistral-small-latest": {"input": 0.20 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
}
DEFAULT_RATE = {"input": 0.50 / 1_000_000, "output": 2.00 / 1_000_000}


def _init_db():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(COST_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost REAL DEFAULT 0.0,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_totals (
            session_id TEXT PRIMARY KEY,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_estimated_cost REAL DEFAULT 0.0,
            turn_count INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def _get_conn() -> sqlite3.Connection:
    _init_db()
    conn = sqlite3.connect(COST_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _get_rate(model: str) -> dict:
    for key, rate in ESTIMATED_RATES.items():
        if key in model:
            return rate
    return DEFAULT_RATE


def track_usage(session_id: str, model: str, input_text: str, output_text: str):
    input_tokens = _estimate_tokens(input_text)
    output_tokens = _estimate_tokens(output_text)
    rate = _get_rate(model)
    cost = (input_tokens * rate["input"] + output_tokens * rate["output"])

    conn = _get_conn()
    conn.execute(
        "INSERT INTO token_usage (session_id, model, input_tokens, output_tokens, estimated_cost) VALUES (?, ?, ?, ?, ?)",
        (session_id, model, input_tokens, output_tokens, round(cost, 6)),
    )
    conn.execute("""
        INSERT INTO session_totals (session_id, total_input_tokens, total_output_tokens, total_estimated_cost, turn_count, last_updated)
        VALUES (?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(session_id) DO UPDATE SET
            total_input_tokens = total_input_tokens + ?,
            total_output_tokens = total_output_tokens + ?,
            total_estimated_cost = total_estimated_cost + ?,
            turn_count = turn_count + 1,
            last_updated = datetime('now')
    """, (session_id, input_tokens, output_tokens, round(cost, 6), input_tokens, output_tokens, round(cost, 6)))
    conn.commit()
    conn.close()


def get_session_usage(session_id: str) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM session_totals WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    conn.close()
    if not row:
        return {"session_id": session_id, "total_input_tokens": 0, "total_output_tokens": 0, "total_estimated_cost": 0.0, "turn_count": 0}
    return dict(row)


def get_session_history(session_id: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM token_usage WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def format_session_cost(session_id: str) -> str:
    usage = get_session_usage(session_id)
    return (
        f"[Session: {session_id}]\n"
        f"  Turns: {usage['turn_count']}\n"
        f"  Input tokens: {usage['total_input_tokens']:,}\n"
        f"  Output tokens: {usage['total_output_tokens']:,}\n"
        f"  Estimated cost: ${usage['total_estimated_cost']:.6f}"
    )
