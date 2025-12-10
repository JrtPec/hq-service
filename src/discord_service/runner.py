"""Discord bot runner for HQ."""

import logging
import typing

import discord
from discord import Intents

from ..game.admin import handle_command, new_mission
from ..game.logger import log_message
from ..game.models.mission import Mission
from .service import DISCORD_TOKEN, send_message_to_channel, set_client

log = logging.getLogger("hq-bot")
logging.basicConfig(level=logging.INFO)


async def start_bot():
    """Start de Discord-bot."""
    if not DISCORD_TOKEN:
        log.warning("Bot niet gestart: ontbrekende ENV (DISCORD_TOKEN)")
        return

    intents = Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    set_client(client)
    missions: dict[str, Mission] = {}

    @client.event
    async def on_ready():
        user = client.user
        client_id = client.user.id if client.user else "unknown"
        log.info("Bot ingelogd als %s (%s)", user, client_id)

    @client.event
    async def on_message(message: discord.Message):
        content = message.content.strip()
        sender = message.author.display_name

        channel = message.channel

        if hasattr(message.channel, "name"):
            channel_name = typing.cast(str, message.channel.name)  # type: ignore
        else:
            channel_name = "unknown"
        try:
            # log.info("Bericht ontvangen van %s: %s", sender, content)
            log_message(channel=channel_name, sender=sender, content=content)
        except Exception as e:
            log.error("Fout bij het loggen van bericht: %s", e)

        response: str | None = None

        if channel_name == "admin" and content.startswith("!"):
            command = content.split()[0]
            message_content = content.split(" ", 1)[1] if " " in content else ""
            if command == "!new":
                mission = await new_mission(message_content)
                missions[mission.name.lower()] = mission
                response = f"✅ Nieuwe missie '{mission.name}' aangemaakt."
            else:
                response = await handle_command(command, message_content)

        elif hasattr(channel.category, "name") and not message.author.bot:  # type: ignore
            category_name = typing.cast(str, channel.category.name)  # type: ignore
            mission = missions.get(category_name)
            if mission is None:
                mission = Mission.load(mission_ref=category_name)
                missions[category_name] = mission
            payload = f"{sender}: {content}"
            try:
                async with message.channel.typing():
                    response = await mission.chat_with_current_stage_bot(payload)
            except Exception as e:
                log.error("Fout bij chat met bot %s: %s", mission.name, e)
                response = f"❌ Fout bij chat met bot {mission.name}: {e}"

        if response:
            await send_message_to_channel(response, message.channel)
            return

    await client.start(DISCORD_TOKEN)
