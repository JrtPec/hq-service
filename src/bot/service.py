import os
import textwrap
import logging
import discord
from discord import Intents

from ..game.main import chat as hq_chat
from ..game.logger import log as game_log

log = logging.getLogger("hq-bot")
logging.basicConfig(level=logging.INFO)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

def _split(text: str, limit: int = 2000):
    if len(text) <= limit:
        return [text]
    return textwrap.wrap(text, width=limit, replace_whitespace=False, drop_whitespace=False)

async def start_bot():
    if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
        log.warning("Bot niet gestart: ontbrekende ENV (DISCORD_TOKEN, DISCORD_CHANNEL_ID)")
        return

    intents = Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

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
        payload = f"{sender}: {content}"

        try:
            await game_log(payload)
        except Exception as e:
            log.error("Fout bij het loggen van bericht: %s", e)

        if not message.author.bot:
            try:
                async with message.channel.typing():
                    reply = await hq_chat(payload)
                if reply:
                    for chunk in _split(reply):
                        await message.channel.send(chunk)
            except Exception as e:
                await message.channel.send(f"❌ HQ API error: {e}")

    # Start Discord-client (asynchroon; sluit niet je FastAPI af)
    await client.start(DISCORD_TOKEN)
