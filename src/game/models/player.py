"""Modellen voor spelers in het spel."""

from typing import Literal

from .participant import Participant


class Player(Participant):
    """Class voor een menselijke speler."""

    type: Literal["player"] = "player"
    inventory: list[str] = []
