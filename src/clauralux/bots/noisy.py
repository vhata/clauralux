"""Wrapper that adds noise to any bot's decisions for training diversity."""

from __future__ import annotations

import random

from clauralux.engine.actions import Action
from clauralux.engine.view import GameView

from .base import Bot


class NoisyWrapper(Bot):
    """Wraps another bot and randomly drops actions to break determinism."""

    def __init__(self, inner: Bot, drop_prob: float = 0.1, seed: int = 0) -> None:
        super().__init__()
        self._inner = inner
        self._drop_prob = drop_prob
        self._rng = random.Random(seed)

    @property
    def intent(self) -> str:
        return self._inner.intent

    def decide(self, view: GameView) -> list[Action]:
        actions = self._inner.decide(view)
        return [a for a in actions if self._rng.random() > self._drop_prob]

    def on_game_start(self, view: GameView) -> None:
        self._inner.on_game_start(view)

    def on_game_end(self, view: GameView) -> None:
        self._inner.on_game_end(view)
