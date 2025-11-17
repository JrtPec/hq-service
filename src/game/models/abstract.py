from abc import ABC
from pathlib import Path
from typing import Self

from pydantic import BaseModel


class AbstractModel(BaseModel, ABC):
    """Abstracte basisclass voor modellen die opgeslagen kunnen worden."""

    name: str
    mission: str

    @classmethod
    def _save_dir(cls, mission) -> Path:
        return Path("data") / mission / (cls.__name__.lower() + "s")

    @classmethod
    def _save_path(cls, mission, name) -> Path:
        return cls._save_dir(mission) / f"{name}.json"

    def save(self):
        """Sla de configuratie op."""
        save_path = self._save_path(self.mission, self.name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, mission, name) -> Self:
        """Laad een deelnemer vanuit een bestand."""
        save_path = cls._save_path(mission, name)
        with open(save_path, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    @classmethod
    def load_all(cls, mission) -> list[Self]:
        """Laad alle modellen vanuit bestanden."""
        instances = []
        if not cls._save_dir(mission).exists():
            return instances
        for instance_file in cls._save_dir(mission).glob("*.json"):
            with open(instance_file, "r", encoding="utf-8") as f:
                instances.append(cls.model_validate_json(f.read()))
        return instances
