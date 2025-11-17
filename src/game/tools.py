"""Hulpprogramma's voor het spel."""

import json
import os
import typing

from .models.player import Player


async def create_player(**kwargs) -> str:
    """Maak een nieuwe speler aan."""
    player = Player.model_validate(kwargs)
    player = typing.cast(Player, player)
    player.save()
    return player.model_dump_json(ensure_ascii=False)


async def get_player(name: str, mission: str) -> str:
    """Haal een speler op op basis van callsign."""
    try:
        player = Player.load(name=name, mission=mission)
        return player.model_dump_json(ensure_ascii=False)
    except FileNotFoundError:
        return "Speler niet gevonden."


async def get_all_players(mission: str) -> str:
    """Haal alle spelers op."""
    players = Player.load_all(mission=mission)
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


async def chat_with_dm(message: str, mission: str) -> str | None:
    """Stuur een bericht naar een bot en ontvang een antwoord."""
    from .models.bot import Commando, get_system_prompt

    try:
        dm = Commando.load(name="COMMANDO", mission=mission)
    except FileNotFoundError:
        dm = Commando(
            name="COMMANDO",
            mission=mission,
            system_prompt=get_system_prompt("src/game/prompts/DM.txt"),
            tool_names=[get_player.__name__, get_all_players.__name__],
        )

    response = await dm.chat(message)
    return response


_tool_functions = [create_player, get_player, get_all_players, get_logs, chat_with_dm]
TOOL_MAP: dict[str, typing.Callable[..., typing.Awaitable[str]]] = {
    func.__name__: func for func in _tool_functions
}
TOOL_SCHEMAS: dict[str, dict] = {
    create_player.__name__: {
        "type": "function",
        "name": create_player.__name__,
        "description": "Maak een nieuwe speler aan in het systeem of overschrijf een bestaande speler.",
        "parameters": Player.tool_schema(),
    },
    get_player.__name__: {
        "type": "function",
        "name": get_player.__name__,
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
    get_all_players.__name__: {
        "type": "function",
        "name": get_all_players.__name__,
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
    get_logs.__name__: {
        "type": "function",
        "name": get_logs.__name__,
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
    chat_with_dm.__name__: {
        "type": "function",
        "name": chat_with_dm.__name__,
        "description": "Stuur een bericht naar het Commando (de spelleiding) en ontvang een antwoord. Stuur een bericht als de spelers een spelactie uitvoeren of als ze iets doen wat het Commando moet weten.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Het bericht dat naar het Commando (de spelleiding) wordt gestuurd.",
                },
            },
            "required": ["message"],
        },
        "return_schema": {
            "type": ["string", "null"],
            "description": "Het antwoord van het Commando (de spelleiding), of null als er geen antwoord is. Geef deze informatie terug aan de spelers zonder wijzigingen.",
        },
    },
}
