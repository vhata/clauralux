from __future__ import annotations

from clauralux.engine.actions import Action
from clauralux.engine.view import GameView

from .base import Bot


class PassiveBot(Bot):
    """Does absolutely nothing. Useful for testing."""

    def decide(self, view: GameView) -> list[Action]:
        return []
