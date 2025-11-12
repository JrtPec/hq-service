import os
from openai import AsyncOpenAI
from pathlib import Path
import json
import datetime as dt


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def append_jsonl(path: Path, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def log_message(sender: str, content: str):
    log_entry = {
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "sender": sender,
        "content": content
    }
    log_path = Path("data") / "game_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(log_path, log_entry)

TOOLS = [
    {
        "type": "function",
        "name": "log_message",
        "description": "Log een bericht naar het logbestand",
        "parameters": {
            "type": "object",
            "properties": {
                "sender": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["sender", "content"],
            "additionalProperties": False,
        },
    }
]

async def log(message: str) -> None:
    """Log een bericht naar het logbestand."""
    system_prompt = "Je bent een logboekfunctie die berichten samenvat en logt. Als het korte berichten zijn, log ze dan direct, als ze langer zijn, vat ze dan samen voordat je ze logt."
    input = [{"role": "user", "content": message}]
    response = await client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_prompt,
        input=input,  # type: ignore
        tools=TOOLS,  # type: ignore
    )
    for item in response.output:
        if item.type == "function_call":
            if item.name == "log_message":
                log_data = json.loads(item.arguments)
                log_message(**log_data)