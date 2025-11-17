from typing import Literal

import discord

from ...discord.service import get_guild
from .abstract import AbstractModel
from .bot import Bot


class Mission(AbstractModel):
    """Class representing a mission in the game."""

    type: Literal["mission"] = "mission"
    stage: Literal["intake", "active", "completed"] = "intake"

    async def get_category(self) -> discord.CategoryChannel:
        """Get a Discord category channel by mission ID."""
        guild = get_guild()
        if guild is None:
            raise RuntimeError("Guild not found.")
        categories = guild.categories

        category_name = self.name.lower()

        for category in categories:
            if category.name == category_name:
                return category

        category = await guild.create_category(name=category_name)
        return category

    async def get_channel(self, channel_name: str) -> discord.TextChannel:
        """Get a Discord text channel by mission ID and channel name."""
        category = await self.get_category()
        for channel in category.text_channels:
            if channel.name == channel_name.lower():
                return channel
        channel = await category.create_text_channel(name=channel_name)
        return channel

    def get_current_stage_bot(
        self,
    ) -> Bot:
        """Return the bot for the current mission stage."""
        try:
            bot = Bot.load(mission=self.name, name=self.stage.upper())
            return bot
        except FileNotFoundError:
            bot = Bot(
                name=self.stage.upper(),
                mission=self.name,
                system_prompt=f"This is the bot for the {self.stage} stage of mission {self.name}.",
            )
        return bot

    async def init_stage(self, stage: Literal["intake", "active", "completed"]) -> None:
        """Initialize the mission to the given stage."""
        self.stage = stage
        channel = await self.get_channel(stage)
        await channel.send(f"Missie {self.name} is nu in de fase: {stage}.")
        self.save()

    async def chat_with_current_stage_bot(self, message: str) -> str | None:
        """Chat with the bot for the current mission stage."""
        bot = self.get_current_stage_bot()
        response = await bot.chat(message)
        return response
