import sqlite3
from pathlib import Path
import os

from openai import AsyncOpenAI

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
DB_PATH = Path(os.getenv("DB_PATH", "conversation.db"))

def init_db() -> sqlite3.Connection:
    """Initialiseer de database en maak de benodigde tabellen aan indien ze nog niet bestaan."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            conversation_id TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

async def get_current_conversation(client: AsyncOpenAI) -> str:
    """Haal de huidige conversatie op uit de database, of maak een nieuwe aan indien er nog geen is."""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT conversation_id FROM conversations ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row and row[0]:
        return row[0]

    # Geen bestaande → nieuwe aanmaken
    conv = await client.conversations.create(
        items=[{"role": "system", "content": SYSTEM_PROMPT}],
    )
    conv_id = conv.id
    conn.execute(
        "INSERT INTO conversations (model, conversation_id) VALUES (?, ?)",
        (OPENAI_MODEL, conv_id),
    )
    conn.commit()
    return conv_id

async def reset_conversation(client: AsyncOpenAI) -> str:
    """Reset de huidige conversatie door alle records te verwijderen en een nieuwe aan te maken."""
    conn = init_db()
    conn.execute("DELETE FROM conversations")
    conn.commit()
    return await get_current_conversation(client)
