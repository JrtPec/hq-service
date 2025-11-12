"""Hoofdlogica voor het spel."""

import json
import os
import typing

import instructor
from openai import AsyncOpenAI

from .models import Bot, Player, get_system_prompt

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = instructor.from_openai(client=AsyncOpenAI(api_key=OPENAI_API_KEY))

HQ = Bot(
    callsign="HQ",
    system_prompt=get_system_prompt("src/game/prompts/HQ.txt"),
)
HQ.save()

TOOLS = [
    {
        "type": "function",
        "name": "create_player",
        "description": "Maak een nieuwe speler aan in het systeem of overschrijf een bestaande speler.",
        "parameters": Player.tool_schema(),
    },
    {
        "type": "function",
        "name": "get_player",
        "description": "Haal een speler op op basis van callsign.",
        "parameters": {
            "type": "object",
            "properties": {
                "callsign": {
                    "type": "string",
                    "description": "Callsign van de speler.",
                },
            },
            "required": ["callsign"],
        },
        "return_schema": Player.tool_schema(),
    },
    {
        "type": "function",
        "name": "get_all_players",
        "description": "Haal alle spelers op.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "return_schema": {
            "type": "array",
            "items": Player.tool_schema(),
        },
    },
    {
        "type": "function",
        "name": "get_logs",
        "description": "Haal de laatste N logberichten op.",
        "parameters": {
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Het aantal logberichten om op te halen.",
                    "default": 10,
                },
            },
            "required": [],
        },
        "return_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts": {
                        "type": "string",
                        "description": "Timestamp van het logbericht.",
                    },
                    "sender": {
                        "type": "string",
                        "description": "Afzender van het bericht.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Inhoud van het bericht.",
                    },
                },
            },
        },
    },
]


async def chat(message: str) -> str | None:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    await HQ.ensure_conversation(client)
    input_list = [{"role": "user", "content": message}]
    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=HQ.conversation_id,
        input=input_list,  # type: ignore
        tools=TOOLS,  # type: ignore
    )

    if response.output_text != "":
        return response.output_text

    for item in response.output:
        if item.type == "function_call":
            func = globals().get(item.name)
            if func:
                result = await func(**json.loads(item.arguments))
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": result,
                    }
                )

    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=HQ.conversation_id,
        input=input_list,  # type: ignore
    )
    if response.output_text != "":
        return response.output_text

    return None


async def create_player(**kwargs) -> str:
    """Maak een nieuwe speler aan."""
    player = Player.model_validate(kwargs)
    player = typing.cast(Player, player)
    player.save()
    return player.model_dump_json(ensure_ascii=False)


async def get_player(callsign: str) -> str:
    """Haal een speler op op basis van callsign."""
    try:
        player = Player.load(callsign)
        return player.model_dump_json(ensure_ascii=False)
    except FileNotFoundError:
        return "Speler niet gevonden."


async def get_all_players() -> str:
    """Haal alle spelers op."""
    players = Player.load_all()
    if not players:
        return "Er zijn geen spelers gevonden."
    players = [player.model_dump_json(ensure_ascii=False) for player in players]
    return json.dumps(players, ensure_ascii=False)


async def get_logs(top_n: int = 10) -> str:
    """Haal de laatste N logberichten op."""
    log_path = "data/game_log.jsonl"
    if not os.path.exists(log_path):
        return "Er zijn geen logberichten gevonden."

    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    last_lines = lines[-top_n:]
    return "[" + ",".join(line.strip() for line in last_lines) + "]"
