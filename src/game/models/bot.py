"""Modellen voor AI-gestuurde bots in het spel."""

import json
import logging
import os
from typing import Literal

from ...discord.service import get_client as get_discord_client
from ...discord.service import send_message_to_channel
from ...openai.client import client as openai_client
from ..tools import TOOL_MAP, TOOL_SCHEMAS
from .participant import Participant

log = logging.getLogger("bot")
logging.basicConfig(level=logging.INFO)


def get_system_prompt(path) -> str:
    """Lees het systeemprompt uit een bestand."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class Bot(Participant):
    """Class voor een AI-gestuurde bot."""

    system_prompt: str
    conversation_id: str | None = None
    type: Literal["bot"] = "bot"
    openai_model: str = "gpt-4o"

    tool_names: list[str] | None = None

    @property
    def _tools(self) -> list[dict]:
        if self.tool_names is None:
            return []
        return [TOOL_SCHEMAS[name] for name in self.tool_names if name in TOOL_SCHEMAS]

    async def ensure_conversation(self):
        """Zorg ervoor dat er een gesprek bestaat voor de bot."""
        if not self.conversation_id:
            log.info("Creating conversation for bot %s", self.name)
            conv = await openai_client.conversations.create(
                items=[{"role": "system", "content": self.system_prompt}],
            )
            log.info("Conversation created with ID %s for bot %s", conv.id, self.name)
            self.conversation_id = conv.id
            # self.save()

    async def chat(
        self,
        message: str,
    ) -> str | None:
        """Stuur een bericht naar de bot en retourneer het antwoord."""
        await self.ensure_conversation()
        input_list = [{"role": "user", "content": message}]
        log.info("Sending message to bot %s: %s", self.name, message)
        response = await openai_client.responses.create(
            model=self.openai_model,
            conversation=self.conversation_id,
            input=input_list,  # type: ignore
            tools=self._tools,
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
                func = TOOL_MAP.get(item.name)
                if func:
                    result = await func(**json.loads(item.arguments))
                    input_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": result,
                        }
                    )

        log.info(
            "Sending follow-up message to bot %s with function call outputs",
            self.name,
        )
        log.info("Follow-up input: %s", input_list)
        response = await openai_client.responses.create(
            model=self.openai_model,
            conversation=self.conversation_id,
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


class Commando(Bot):
    """Class voor het Commando-bot."""

    name: str = "COMMANDO"
    openai_model: str = "gpt-4o"
    channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID_COMMAND", "0"))

    @property
    def discord_channel(self):
        discord_client = get_discord_client()
        if discord_client is None:
            raise RuntimeError("Discord client is not started.")
        channel = discord_client.get_channel(self.channel_id)
        return channel

    async def chat(
        self,
        message: str,
    ) -> str | None:
        """Stuur een bericht naar het Commando-bot en retourneer het antwoord."""
        response = await super().chat(message)
        if response:
            await send_message_to_channel(response, self.discord_channel)
        return response
