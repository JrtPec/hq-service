"""Modellen voor AI-gestuurde bots in het spel."""

import logging
from typing import Literal

from ...openai_service.client import client as openai_client
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
