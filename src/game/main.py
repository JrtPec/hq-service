"""Hoofdlogica voor het spel."""

from .models.bot import Bot, get_system_prompt
from .tools import chat_with_dm, create_player, get_all_players, get_logs, get_player

hq_tool_names = [
    create_player.__name__,
    get_player.__name__,
    get_all_players.__name__,
    get_logs.__name__,
    chat_with_dm.__name__,
]
try:
    HQ = Bot.load(callsign="HQ")
except FileNotFoundError:
    HQ = Bot(
        callsign="HQ",
        system_prompt=get_system_prompt("src/game/prompts/HQ.txt"),
        tool_names=hq_tool_names,
    )
else:
    # Zorg ervoor dat de tools up-to-date zijn
    HQ.tool_names = hq_tool_names


async def chat(message: str) -> str | None:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    response = await HQ.chat(message)
    return response
