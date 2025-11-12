"""Modellen voor spelers in het spel."""

from pathlib import Path
from typing import Literal

from .participant import Participant


class Player(Participant):
    """Class voor een menselijke speler."""

    type: Literal["player"] = "player"

    @classmethod
    def _save_dir(cls) -> Path:
        return Path("data") / "players"
