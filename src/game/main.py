"""Hoofdlogica voor het spel."""

import os

import instructor
from openai import AsyncOpenAI

from .models.bot import Bot, get_system_prompt
from .tools import create_player, get_all_players, get_logs, get_player

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = instructor.from_openai(client=AsyncOpenAI(api_key=OPENAI_API_KEY))

HQ = Bot(
    callsign="HQ",
    system_prompt=get_system_prompt("src/game/prompts/HQ.txt"),
    tool_names=[
        create_player.__name__,
        get_player.__name__,
        get_all_players.__name__,
        get_logs.__name__,
    ],
)
HQ.save()

DM = Bot(
    callsign="DM",
    system_prompt=get_system_prompt("src/game/prompts/DM.txt"),
    tool_names=[get_player.__name__, get_all_players.__name__],
)
DM.save()


async def chat(message: str) -> str | None:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    response = await HQ.chat(client, message)
    return response
