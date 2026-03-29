from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView

from .base import Bot


class SwarmBot(Bot):
    """Many small attacks from every sun, every tick. Death by a thousand cuts."""

    def __init__(self, send_size: int = 3, act_interval: int = 15) -> None:
        super().__init__()
        self._send_size = send_size
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. Swarmed out."
            return []

        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "Everything is mine. The swarm has consumed all."
            return []

        actions: list[Action] = []
        groups_launched = 0

        for sun in my_suns:
            if sun.garrison < self._send_size + 1:
                continue

            # Find the nearest target to this specific sun.
            nearest = min(targets, key=lambda t: sun.position.distance_to(t.position))
            actions.append(SendUnits(sun.id, nearest.id, self._send_size))
            groups_launched += 1

        if groups_launched > 0:
            self._intent = f"Swarming — {groups_launched} groups launched at nearby targets."
        else:
            self._intent = "Building up for the next wave."

        return actions
