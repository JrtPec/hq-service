"""Modellen voor deelnemers aan het spel (spelers en bots)."""

from typing import Literal

from pydantic import BaseModel


class Participant(BaseModel):
    """Abstracte basisclass voor een deelnemer (speler of bot)."""

    name: str
    type: Literal["player", "bot"]
    inventory: list[str] | None = None
    notes: str | None = None

    @classmethod
    def tool_schema(cls) -> dict:
        """Retourneer het schema voor tool-registratie."""
        schema = cls.model_json_schema(mode="serialization")
        schema.pop("title", None)
        schema.pop("$defs", None)
        return schema
