"""Modellen voor AI-gestuurde bots in het spel."""

import json
import logging
from pathlib import Path
from typing import Literal

import instructor

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

    @classmethod
    def _save_dir(cls) -> Path:
        return Path("data") / "bots"

    async def ensure_conversation(self, client: instructor.AsyncInstructor):
        """Zorg ervoor dat er een gesprek bestaat voor de bot."""
        if not self.conversation_id:
            log.info("Creating conversation for bot %s", self.callsign)
            conv = await client.conversations.create(
                items=[{"role": "system", "content": self.system_prompt}],
            )
            log.info(
                "Conversation created with ID %s for bot %s", conv.id, self.callsign
            )
            self.conversation_id = conv.id
            self.save()

    async def chat(
        self,
        client: instructor.AsyncInstructor,
        message: str,
    ) -> str | None:
        """Stuur een bericht naar de bot en retourneer het antwoord."""
        await self.ensure_conversation(client)
        input_list = [{"role": "user", "content": message}]
        log.info("Sending message to bot %s: %s", self.callsign, message)
        response = await client.responses.create(
            model=self.openai_model,
            conversation=self.conversation_id,
            input=input_list,  # type: ignore
            tools=self._tools,
        )
        if response.output_text != "":
            log.info(
                "Received response from bot %s: %s", self.callsign, response.output_text
            )
            return response.output_text

        for item in response.output:
            if item.type == "function_call":
                log.info(
                    "Bot %s is calling function %s with arguments %s",
                    self.callsign,
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
            self.callsign,
        )
        log.info("Follow-up input: %s", input_list)
        response = await client.responses.create(
            model=self.openai_model,
            conversation=self.conversation_id,
            input=input_list,  # type: ignore
        )
        if response.output_text != "":
            log.info(
                "Received follow-up response from bot %s: %s",
                self.callsign,
                response.output_text,
            )
            return response.output_text

        log.info("No response from bot %s", self.callsign)
        return None
