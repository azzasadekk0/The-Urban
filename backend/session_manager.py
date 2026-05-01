"""
SQLite-backed session manager.
Stores per-session conversation history so the agent has multi-turn context.
"""

import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

import aiosqlite
from backend.config import settings

DB_PATH = str(settings.SQLITE_DB_PATH)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    context_type TEXT DEFAULT 'general',
    history TEXT DEFAULT '[]'
);
"""


async def _get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute(CREATE_TABLE)
    await db.commit()
    return db


# Public API 

async def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db = await _get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (session_id, created_at, updated_at) VALUES (?, ?, ?)",
            (session_id, now, now),
        )
        await db.commit()
    finally:
        await db.close()
    return session_id


async def get_session(session_id: str) -> dict | None:
    """Retrieve session data or None if not found."""
    db = await _get_db()
    try:
        async with db.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["history"] = json.loads(data["history"])
            return data
    finally:
        await db.close()


async def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    session = await get_session(session_id)
    if session is None:
        await create_session()
        session = await get_session(session_id)

    history: list = session["history"]
    history.append({"role": role, "content": content, "ts": datetime.utcnow().isoformat()})

    # Keep last 20 messages to avoid unbounded growth
    history = history[-20:]
    now = datetime.utcnow().isoformat()

    db = await _get_db()
    try:
        await db.execute(
            "UPDATE sessions SET history = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(history, ensure_ascii=False), now, session_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_history(session_id: str) -> list[dict]:
    """Return conversation history for a session."""
    session = await get_session(session_id)
    return session["history"] if session else []


async def update_session_meta(session_id: str, language: str, context_type: str) -> None:
    now = datetime.utcnow().isoformat()
    db = await _get_db()
    try:
        await db.execute(
            "UPDATE sessions SET language = ?, context_type = ?, updated_at = ? WHERE session_id = ?",
            (language, context_type, now, session_id),
        )
        await db.commit()
    finally:
        await db.close()


async def delete_session(session_id: str) -> None:
    db = await _get_db()
    try:
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.commit()
    finally:
        await db.close()


async def list_sessions() -> list[dict]:
    """Return all sessions ordered by most recently updated, with a preview of the first user message."""
    db = await _get_db()
    try:
        async with db.execute(
            "SELECT session_id, created_at, updated_at, language, history FROM sessions ORDER BY updated_at DESC LIMIT 50"
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                data = dict(row)
                history = json.loads(data.get("history", "[]"))
                # Find first user message as the preview title
                first_user = next((m["content"] for m in history if m["role"] == "user"), None)
                results.append({
                    "session_id": data["session_id"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "language": data["language"],
                    "message_count": len(history),
                    "preview": (first_user[:80] + "…") if first_user and len(first_user) > 80 else first_user,
                })
            return results
    finally:
        await db.close()
