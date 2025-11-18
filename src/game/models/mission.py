import enum
import json
import logging
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel

import discord

from ...discord.service import get_guild
from ...openai.client import client as openai_client
from .bot import Bot, get_system_prompt
from .player import Player

log = logging.getLogger("mission")
logging.basicConfig(level=logging.INFO)


class MissionStage(enum.Enum):
    INTAKE = "intake"
    ACTIVE = "active"
    COMPLETED = "completed"


class Mission(BaseModel):
    """Class representing a mission in the game."""

    name: str
    type: Literal["mission"] = "mission"
    stage: MissionStage = MissionStage.INTAKE

    _category: discord.CategoryChannel | None = None
    _channels: dict[MissionStage, discord.TextChannel] | None = None

    bots: dict[MissionStage, Bot] = {}
    players: list[Player] = []

    @classmethod
    def _save_dir(cls, mission_ref) -> Path:
        return Path("data") / mission_ref

    @classmethod
    def _save_path(cls, name) -> Path:
        return cls._save_dir(name) / "mission.json"

    def save(self):
        """Sla de configuratie op."""
        save_path = self._save_path(self.name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, mission_ref) -> Self:
        """Laad een deelnemer vanuit een bestand."""
        save_path = cls._save_path(mission_ref)
        with open(save_path, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    async def init_category(self) -> discord.CategoryChannel:
        """Get a Discord category channel by mission ID."""
        guild = get_guild()
        if guild is None:
            raise RuntimeError("Guild not found.")
        categories = guild.categories

        category_name = self.name.lower()

        for category in categories:
            if category.name == category_name:
                break
        else:
            category = await guild.create_category(name=category_name)
        self._category = category
        return category

    async def get_channel(self, channel_name: str) -> discord.TextChannel:
        """Get a Discord text channel by mission ID and channel name."""
        if self._category is None:
            raise RuntimeError("Category not initialized.")
        for channel in self._category.text_channels:
            if channel.name == channel_name.lower():
                return channel
        channel = await self._category.create_text_channel(name=channel_name)
        return channel

    def get_current_stage_bot(
        self,
    ) -> Bot:
        """Return the bot for the current mission stage."""
        bot = self.bots.get(self.stage)
        if bot is not None:
            return bot
        bot = self.load_stage_bot(stage=self.stage)
        self.bots[self.stage] = bot
        return bot

    async def init_stage(self, stage: MissionStage) -> None:
        """Initialize the mission to the given stage."""
        self.stage = stage
        channel = await self.get_channel(channel_name=stage.value)
        if self._channels is None:
            self._channels = {}
        self._channels[stage] = channel
        bot = self.load_stage_bot(stage=stage)
        await bot.ensure_conversation()
        self.bots[stage] = bot
        await channel.send(f"Missie {self.name} is nu in de fase: {stage}.")
        self.save()

    async def close_stage(self, stage: MissionStage) -> None:
        """Close the given mission stage."""
        if self._channels and stage in self._channels:
            channel = self._channels[stage]
            await channel.send(f"Missie {self.name} fase {stage} is afgesloten.")
            # Set channel to read-only
            overwrites = channel.overwrites
            overwrites[discord.utils.get(channel.guild.roles, name="@everyone")] = (  # type: ignore
                discord.PermissionOverwrite(read_messages=True, send_messages=False)
            )
            await channel.edit(overwrites=overwrites)
        self.save()

    async def init_next_stage(self) -> None:
        """Initialize the next mission stage."""
        if self.stage == MissionStage.INTAKE:
            await self.close_stage(MissionStage.INTAKE)
            await self.init_stage(MissionStage.ACTIVE)
        elif self.stage == MissionStage.ACTIVE:
            await self.close_stage(MissionStage.ACTIVE)
            await self.init_stage(MissionStage.COMPLETED)
        else:
            raise RuntimeError("No next stage available.")

    async def chat_with_current_stage_bot(self, message: str) -> str | None:
        """Chat with the bot for the current mission stage."""
        bot = self.get_current_stage_bot()
        response = await self.chat_with_bot(bot, message)
        return response

    async def chat_with_bot(self, bot: Bot, message: str) -> str | None:
        """Chat with a specific bot."""
        input_list = [{"role": "user", "content": message}]
        log.info("Sending message to bot %s: %s", self.name, message)
        response = await openai_client.responses.create(
            model=bot.openai_model,
            conversation=bot.conversation_id,
            input=input_list,  # type: ignore
            tools=TOOLS,
        )
        if response.output_text != "":
            log.info(
                "Received response from bot %s: %s", self.name, response.output_text
            )
            return response.output_text

        for item in response.output:
            if item.type == "function_call":
                log.info(
                    "Bot %s is calling function %s with arguments %s",
                    self.name,
                    item.name,
                    item.arguments,
                )
                if item.name == "create_player":
                    func = self.create_player
                elif item.name == "get_all_players":
                    func = self.get_all_players
                elif item.name == "next_stage":
                    func = self.next_stage
                else:
                    func = None
                if func:
                    result = await func(**json.loads(item.arguments))
                    input_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": result,
                        }
                    )
                else:
                    log.warning("Unknown function call: %s", item.name)
                    return None

        log.info(
            "Sending follow-up message to bot %s with function call outputs",
            self.name,
        )
        log.info("Follow-up input: %s", input_list)
        response = await openai_client.responses.create(
            model=bot.openai_model,
            conversation=bot.conversation_id,
            input=input_list,  # type: ignore
        )
        if response.output_text != "":
            log.info(
                "Received follow-up response from bot %s: %s",
                self.name,
                response.output_text,
            )
            return response.output_text

        log.info("No response from bot %s", self.name)
        return None

    def load_stage_bot(self, stage: MissionStage) -> Bot:
        if self.stage == MissionStage.INTAKE:
            bot = Bot(
                name=MissionStage.INTAKE.value,
                system_prompt=get_system_prompt("src/game/prompts/intake.txt"),
            )
            return bot
        bot = Bot(
            name=stage.value,
            system_prompt=f"This is the bot for the {stage} stage of mission {self.name}.",
        )
        return bot

    async def create_player(self, **kwargs) -> str:
        """Create a new player in the mission."""
        player = Player(**kwargs)
        self.players.append(player)
        self.save()
        return player.model_dump_json(ensure_ascii=False)

    async def get_all_players(self) -> str:
        """Get all players in the mission."""
        if not self.players:
            return "Er zijn geen spelers gevonden."
        players = [
            player.model_dump_json(ensure_ascii=False) for player in self.players
        ]
        return json.dumps(players, ensure_ascii=False)

    async def next_stage(self) -> str:
        """Advance the mission to the next stage."""
        await self.init_next_stage()
        return f"Missie {self.name} is nu in de fase: {self.stage}."


TOOLS = [
    {
        "type": "function",
        "name": "create_player",
        "description": "Maak een nieuwe speler aan in de missie met de gegeven eigenschappen.",
        "parameters": Player.tool_schema(),
    },
    {
        "type": "function",
        "name": "get_all_players",
        "description": "Haal alle spelers op in de missie.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "next_stage",
        "description": "Breng de missie naar de volgende fase.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
