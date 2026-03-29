from __future__ import annotations

import random

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView

from .base import Bot


class RandomBot(Bot):
    """Makes random moves. Chaotic but useful as a baseline."""

    def __init__(self, seed: int | None = None, act_probability: float = 0.1) -> None:
        self._rng = random.Random(seed)
        self._act_probability = act_probability

    def decide(self, view: GameView) -> list[Action]:
        if self._rng.random() > self._act_probability:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            return []

        actions: list[Action] = []
        sun = self._rng.choice(my_suns)

        # Randomly decide: send units or upgrade
        if self._rng.random() < 0.2 and sun.level < view.config.max_sun_level:
            actions.append(UpgradeSun(sun.id))
        elif sun.garrison > 2:
            targets = [s for s in view.suns if s.id != sun.id]
            if targets:
                target = self._rng.choice(targets)
                count = self._rng.randint(1, sun.garrison)
                actions.append(SendUnits(sun.id, target.id, count))

        return actions
