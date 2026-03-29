from __future__ import annotations

from abc import ABC, abstractmethod

from clauralux.engine.actions import Action
from clauralux.engine.view import GameView


class Bot(ABC):
    """Base class for all bots. Implement `decide` to play."""

    @abstractmethod
    def decide(self, view: GameView) -> list[Action]:
        """Given the current game view, return a list of actions to take this tick.

        Return an empty list to do nothing.
        Most bots only act every N ticks — that's fine.
        """
        ...

    def on_game_start(self, view: GameView) -> None:  # noqa: B027
        """Called once at game start. Override for setup."""

    def on_game_end(self, view: GameView) -> None:  # noqa: B027
        """Called once when the game ends. Override for cleanup/logging."""
