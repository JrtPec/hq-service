"""Discord utility functions for HQ."""

import logging
import os
import textwrap

import discord

log = logging.getLogger("hq-bot")
logging.basicConfig(level=logging.INFO)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

client: discord.Client | None = None  # Module-level client variable


def set_client(instance: discord.Client):
    """Set the Discord client instance (called by runner)."""
    global client
    client = instance


def get_client() -> discord.Client | None:
    """Return the Discord client instance, or None if not started."""
    return client


async def send_message_to_channel(message: str, channel):
    """Stuur een bericht naar een Discord-kanaal, splits indien nodig."""
    try:
        # log.info("Sending message to channel %s: %s", channel.id, message)
        for chunk in _split(message):
            await channel.send(chunk)
    except Exception as e:
        log.error("Error sending message to channel %s: %s", channel.id, e)


def _split(text: str, limit: int = 2000):
    if len(text) <= limit:
        return [text]
    return textwrap.wrap(
        text, width=limit, replace_whitespace=False, drop_whitespace=False
    )
