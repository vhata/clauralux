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

        # Check if we can concentrate fire on a high-priority target.
        available_suns = [s for s in my_suns if s.garrison >= self._send_size + 1]
        total_available = len(available_suns) * self._send_size

        if total_available > 0:
            # Find the weakest target overall.
            weakest = min(targets, key=lambda t: t.garrison)
            if weakest.garrison <= total_available // 2 and len(available_suns) >= 2:
                # Concentrate fire: send from the 2 nearest suns to this one target.
                nearest_suns = sorted(
                    available_suns,
                    key=lambda s: s.position.distance_to(weakest.position),
                )[:2]
                actions: list[Action] = [
                    SendUnits(s.id, weakest.id, self._send_size) for s in nearest_suns
                ]
                self._intent = (
                    f"Concentrating fire — {len(actions)} groups targeting"
                    f" Sun {weakest.id} (garrison {weakest.garrison})."
                )
                return actions

        # Fallback: spread attacks from every sun to its nearest target.
        actions = []
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
