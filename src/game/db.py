import datetime as dt
import sqlite3
import os
import json

from openai import AsyncOpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

def resolve_db_path():
    """Bepaal het pad voor de SQLite-database."""
    db_path = os.getenv("DB_PATH", "")
    if not db_path:
        db_path = "/tmp/db.db"
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    except (PermissionError, OSError):
        # fallback
        db_path = "/tmp/db.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path

DB_PATH = resolve_db_path()

def init_db() -> sqlite3.Connection:
    """Initialiseer de database en maak de benodigde tabellen aan indien ze nog niet bestaan."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_name TEXT NOT NULL UNIQUE,
            model TEXT,
            conversation_id TEXT UNIQUE,
            is_concluded INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

async def get_conversation(client: AsyncOpenAI, partner_name: str, system_prompt: str = "") -> str:
    """Haal de conversatie voor een partner op, of maak een nieuwe aan indien er nog geen open conversatie is."""
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        """
            SELECT conversation_id
            FROM conversations
            WHERE partner_name = ?
        """,
        (partner_name,),
    )
    row = cur.fetchone()
    if row and row[0]:
        return row[0]

    # Geen bestaande → nieuwe aanmaken
    conv = await client.conversations.create(
        items=[{"role": "system", "content": system_prompt}],
    )
    conv_id = conv.id
    conn.execute(
        "INSERT INTO conversations (model, conversation_id, partner_name) VALUES (?, ?, ?)",
        (OPENAI_MODEL, conv_id, partner_name),
    )
    conn.commit()
    return conv_id

def close_conversation(partner_name: str) -> None:
    """Markeer een conversatie als afgerond zodat er later een nieuwe gestart kan worden."""
    conn = init_db()
    conn.execute(
        """
            UPDATE conversations
            SET is_concluded = 1
            WHERE partner_name = ?
        """,
        (partner_name,),
    )
    conn.commit()

def reopen_conversation(partner_name: str) -> None:
    """Heropen een afgeronde conversatie."""
    conn = init_db()
    conn.execute(
        """
            UPDATE conversations
            SET is_concluded = 0
            WHERE partner_name = ?
        """,
        (partner_name,),
    )
    conn.commit()

def log_event(
    mission_code: str,
    event_code: str,
    notes: str,
    state: dict | None = None,
) -> dict:
    """
    Log een event vanuit HQ of een andere agent.
    """
    payload = {
        "mission_code": mission_code,
        "event_code": event_code,
        "notes": notes,
        "state": state or {},
    }

    conn = init_db()
    c = conn.cursor()
    
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS logbook (
            timestamp TEXT,
            mission_code TEXT,
            event_code TEXT,
            notes TEXT,
            state_json TEXT
        )
        """
    )
    c.execute(
        "INSERT INTO logbook VALUES (?, ?, ?, ?, ?)",
        (
            dt.datetime.utcnow().isoformat(),
            mission_code,
            event_code,
            notes,
            json.dumps(state or {}),
        ),
    )
    conn.commit()
    conn.close()
    return payload
