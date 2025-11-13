"""Discord bot runner for HQ."""

import logging

import discord
from discord import Intents

from ..game.logger import log_message
from ..game.main import chat as hq_chat
from .service import (
    DISCORD_CHANNEL_ID,
    DISCORD_TOKEN,
    send_message_to_channel,
    set_client,
)

log = logging.getLogger("hq-bot")
logging.basicConfig(level=logging.INFO)


async def start_bot():
    """Start de Discord-bot."""
    if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
        log.warning(
            "Bot niet gestart: ontbrekende ENV (DISCORD_TOKEN, DISCORD_CHANNEL_ID)"
        )
        return

    intents = Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    set_client(client)

    @client.event
    async def on_ready():
        user = client.user
        client_id = client.user.id if client.user else "unknown"
        log.info("Bot ingelogd als %s (%s)", user, client_id)

    @client.event
    async def on_message(message: discord.Message):
        if message.channel.id != DISCORD_CHANNEL_ID:
            return

        content = message.content.strip()
        sender = message.author.display_name
        try:
            # log.info("Bericht ontvangen van %s: %s", sender, content)
            log_message(sender=sender, content=content)
        except Exception as e:
            log.error("Fout bij het loggen van bericht: %s", e)

        if not message.author.bot:
            payload = f"{sender}: {content}"
            try:
                async with message.channel.typing():
                    reply = await hq_chat(payload)
                if reply:
                    await send_message_to_channel(reply, message.channel)
            except Exception as e:
                await message.channel.send(f"❌ HQ API error: {e}")

    await client.start(DISCORD_TOKEN)
