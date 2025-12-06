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
from .location import Location
from .player import Player

log = logging.getLogger("mission")
logging.basicConfig(level=logging.INFO)


class MissionStage(enum.Enum):
    INTAKE = "intake"
    BEACON = "beacon"
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
    hq_location: Location | None = None
    drop_point: Location | None = None

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
        channel = await self.get_channel(channel_name=stage.value)
        if self._channels is None:
            self._channels = {}
        self._channels[stage] = channel
        bot = self.load_stage_bot(stage=stage)
        await bot.ensure_conversation()
        self.bots[stage] = bot
        self.stage = stage
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

    def is_stage_completed(self, stage: MissionStage) -> tuple[bool, str]:
        """Check if a mission stage is completed."""
        if stage == MissionStage.INTAKE:
            if not self.players:
                return False, "Er zijn nog geen spelers geregistreerd."
            if self.hq_location is None:
                return False, "De HQ-locatie is nog niet ingesteld."
            return True, "Intake fase is voltooid."
        elif stage == MissionStage.BEACON:
            return True, "Beacon fase is voltooid."
        elif stage == MissionStage.ACTIVE:
            # Add checks for ACTIVE stage completion if needed
            return True, "Active fase is voltooid."
        elif stage == MissionStage.COMPLETED:
            # Add checks for COMPLETED stage completion if needed
            return True, "Completed fase is voltooid."
        else:
            return False, "Onbekende missie fase."

    async def init_next_stage(self) -> None:
        """Initialize the next mission stage."""
        if self.stage == MissionStage.INTAKE:
            await self.close_stage(MissionStage.INTAKE)
            await self.init_stage(MissionStage.BEACON)
        elif self.stage == MissionStage.BEACON:
            await self.close_stage(MissionStage.BEACON)
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
        self.save()
        return response

    async def chat_with_bot(self, bot: Bot, message: str) -> str | None:
        """Chat with a specific bot."""
        input_list = [{"role": "user", "content": message}]
        log.info("Sending message to bot %s: %s", self.name, message)
        await bot.ensure_conversation()
        response = await openai_client.responses.create(
            model=bot.openai_model,
            conversation=bot.conversation_id,
            input=input_list,  # type: ignore
            tools=[
                tool
                for tool in TOOLS
                if bot.tool_names and tool["name"] in bot.tool_names
            ],
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
                if item.name == "create_or_update_player":
                    func = self.create_or_update_player
                elif item.name == "get_all_players":
                    func = self.get_all_players
                elif item.name == "next_stage":
                    func = self.next_stage
                elif item.name == "set_hq_location":
                    func = self.set_hq_location
                elif item.name == "calculate_distance_to_drop_zone":
                    func = self.calculate_distance_to_drop_zone
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
        """Load the bot for a specific mission stage."""
        if stage == MissionStage.INTAKE:
            bot = Bot(
                name=MissionStage.INTAKE.value,
                system_prompt=get_system_prompt("src/game/prompts/intake.txt"),
                tool_names=[
                    "create_or_update_player",
                    "get_all_players",
                    "next_stage",
                    "set_hq_location",
                ],
            )
        elif stage == MissionStage.BEACON:
            bot = Bot(
                name=MissionStage.BEACON.value,
                system_prompt=get_system_prompt("src/game/prompts/Beacon.txt"),
                tool_names=[
                    "calculate_distance_to_drop_zone",
                    "next_stage",
                ],
            )
        else:
            bot = Bot(
                name=stage.value,
                system_prompt=f"This is the bot for the {stage} stage of mission {self.name}.",
            )
        return bot

    async def create_or_update_player(self, **kwargs) -> str:
        """Create or update a player in the mission."""
        player = Player(**kwargs)
        # Overwrite existing player with same name, else append
        for i, existing_player in enumerate(self.players):
            if existing_player.name == player.name:
                self.players[i] = player
                break
        else:
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
        completed, message = self.is_stage_completed(self.stage)
        if not completed:
            return f"Kan niet naar de volgende fase gaan: {message}"
        await self.init_next_stage()
        return f"Missie {self.name} is nu in de fase: {self.stage}."

    async def set_hq_location(
        self,
        latitude_decimal: float | None = None,
        longitude_decimal: float | None = None,
        latitude_dms: dict | None = None,
        longitude_dms: dict | None = None,
    ) -> str:
        """Set the HQ location for the mission."""
        if (latitude_decimal is not None and latitude_decimal != 0) and (
            longitude_decimal is not None and longitude_decimal != 0
        ):
            self.hq_location = Location(
                latitude=latitude_decimal, longitude=longitude_decimal
            )
        elif latitude_dms is not None and longitude_dms is not None:
            self.hq_location = Location.from_coordinates(
                lat_deg=latitude_dms["degrees"],
                lat_min=latitude_dms["minutes"],
                lat_sec=latitude_dms["seconds"],
                lat_dir=latitude_dms["direction"],
                lon_deg=longitude_dms["degrees"],
                lon_min=longitude_dms["minutes"],
                lon_sec=longitude_dms["seconds"],
                lon_dir=longitude_dms["direction"],
            )
        else:
            return "Ongeldige locatiegegevens verstrekt."
        self.drop_point = self.hq_location.random_location_at_distance(distance_km=10.0)
        self.save()
        return f"HQ-locatie ingesteld op: {self.hq_location.latitude}, {self.hq_location.longitude}."

    async def calculate_distance_to_drop_zone(
        self,
        latitude_decimal: float | None = None,
        longitude_decimal: float | None = None,
        latitude_dms: dict | None = None,
        longitude_dms: dict | None = None,
    ) -> str:
        """Calculate the distance to the drop zone from given coordinates."""
        if (latitude_decimal is not None and latitude_decimal != 0) and (
            longitude_decimal is not None and longitude_decimal != 0
        ):
            location = Location(latitude=latitude_decimal, longitude=longitude_decimal)
        elif latitude_dms is not None and longitude_dms is not None:
            location = Location.from_coordinates(
                lat_deg=latitude_dms["degrees"],
                lat_min=latitude_dms["minutes"],
                lat_sec=latitude_dms["seconds"],
                lat_dir=latitude_dms["direction"],
                lon_deg=longitude_dms["degrees"],
                lon_min=longitude_dms["minutes"],
                lon_sec=longitude_dms["seconds"],
                lon_dir=longitude_dms["direction"],
            )
        else:
            return "Ongeldige locatiegegevens verstrekt."
        if self.drop_point is None:
            return "De drop zone is nog niet ingesteld."
        distance_m = location.distance_to(self.drop_point)
        return f"De afstand tot de drop zone is {int(distance_m)} meter."


TOOLS = [
    {
        "type": "function",
        "name": "create_or_update_player",
        "description": "Maak een nieuwe speler aan of werk een bestaande speler bij in de missie met de gegeven eigenschappen.",
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
    {
        "type": "function",
        "name": "set_hq_location",
        "description": "Stel de HQ-locatie in voor de missie, gegeven in decimale graden of in DMS-formaat.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude_decimal": {
                    "type": "number",
                    "description": "Latitude in decimal degrees.",
                },
                "longitude_decimal": {
                    "type": "number",
                    "description": "Longitude in decimal degrees.",
                },
                "latitude_dms": {
                    "type": "object",
                    "properties": {
                        "degrees": {"type": "integer", "description": "Degrees"},
                        "minutes": {"type": "integer", "description": "Minutes"},
                        "seconds": {"type": "integer", "description": "Seconds"},
                        "direction": {
                            "type": "string",
                            "enum": ["N", "S"],
                            "description": "Direction",
                        },
                    },
                    "required": ["degrees", "minutes", "seconds", "direction"],
                    "description": "Latitude in DMS format.",
                },
                "longitude_dms": {
                    "type": "object",
                    "properties": {
                        "degrees": {"type": "integer", "description": "Degrees"},
                        "minutes": {"type": "integer", "description": "Minutes"},
                        "seconds": {"type": "integer", "description": "Seconds"},
                        "direction": {
                            "type": "string",
                            "enum": ["E", "W"],
                            "description": "Direction",
                        },
                    },
                    "required": ["degrees", "minutes", "seconds", "direction"],
                    "description": "Longitude in DMS format.",
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "calculate_distance_to_drop_zone",
        "description": "Bereken de afstand tot de drop zone vanaf de gegeven coördinaten, in decimale graden of in DMS-formaat.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude_decimal": {
                    "type": "number",
                    "description": "Latitude in decimal degrees.",
                },
                "longitude_decimal": {
                    "type": "number",
                    "description": "Longitude in decimal degrees.",
                },
                "latitude_dms": {
                    "type": "object",
                    "properties": {
                        "degrees": {"type": "integer", "description": "Degrees"},
                        "minutes": {"type": "integer", "description": "Minutes"},
                        "seconds": {"type": "integer", "description": "Seconds"},
                        "direction": {
                            "type": "string",
                            "enum": ["N", "S"],
                            "description": "Direction",
                        },
                    },
                    "required": ["degrees", "minutes", "seconds", "direction"],
                    "description": "Latitude in DMS format.",
                },
                "longitude_dms": {
                    "type": "object",
                    "properties": {
                        "degrees": {"type": "integer", "description": "Degrees"},
                        "minutes": {"type": "integer", "description": "Minutes"},
                        "seconds": {"type": "integer", "description": "Seconds"},
                        "direction": {
                            "type": "string",
                            "enum": ["E", "W"],
                            "description": "Direction",
                        },
                    },
                    "required": ["degrees", "minutes", "seconds", "direction"],
                    "description": "Longitude in DMS format.",
                },
            },
            "required": [],
        },
    },
]
