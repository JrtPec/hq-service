"""Logging functionaliteit voor het spel."""

import datetime as dt
import json
from pathlib import Path


def append_jsonl(path: Path, obj: dict):
    """Append een object als JSONL naar het bestand op het opgegeven pad."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log_message(channel: str, sender: str, content: str):
    """Log een bericht van een speler naar het game log bestand."""
    log_entry = {
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "channel": channel,
        "sender": sender,
        "content": content,
    }
    log_path = Path("data") / "game_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(log_path, log_entry)
