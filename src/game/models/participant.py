"""Modellen voor deelnemers aan het spel (spelers en bots)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from instructor import OpenAISchema


class Participant(OpenAISchema, ABC):
    """Abstracte basisclass voor een deelnemer (speler of bot)."""

    callsign: str
    type: Literal["player", "bot"]
    inventory: list[str] | None = None
    notes: str | None = None

    @classmethod
    @abstractmethod
    def _save_dir(cls) -> Path:
        raise NotImplementedError("Subclasses must implement _save_dir method")

    @property
    def _save_path(self) -> Path:
        return self._save_dir() / f"{self.callsign}.json"

    def save(self):
        """Sla de configuratie op."""
        participant_path = self._save_path
        participant_path.parent.mkdir(parents=True, exist_ok=True)
        with open(participant_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, ensure_ascii=False))

    @classmethod
    def tool_schema(cls) -> dict:
        """Retourneer het schema voor tool-registratie."""
        schema = cls.model_json_schema(mode="serialization")
        schema.pop("title", None)
        schema.pop("$defs", None)
        return schema

    @classmethod
    def load(cls, name: str) -> "Participant":
        """Laad een deelnemer vanuit een bestand."""
        participant_path = cls._save_dir() / f"{name}.json"
        with open(participant_path, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    @classmethod
    def load_all(cls) -> list["Participant"]:
        """Laad alle deelnemers vanuit bestanden."""
        participants = []
        if not cls._save_dir().exists():
            return participants
        for participant_file in cls._save_dir().glob("*.json"):
            with open(participant_file, "r", encoding="utf-8") as f:
                participants.append(cls.model_validate_json(f.read()))
        return participants
