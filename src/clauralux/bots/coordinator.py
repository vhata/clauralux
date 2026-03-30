from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView, SunView

from .base import Bot


class CoordinatorBot(Bot):
    """Accumulates across multiple suns, then strikes several targets at once."""

    def __init__(self, reserve: int = 3, act_interval: int = 80, min_garrison: int = 12) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval
        self._min_garrison = min_garrison

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not my_suns or not targets:
            self._intent = "Nothing to coordinate." if not targets else "No suns left."
            return []

        # Find suns that are ready to attack (enough garrison).
        ready_suns = [s for s in my_suns if s.garrison >= self._min_garrison]
        if not ready_suns:
            self._intent = (
                f"Building up — need {self._min_garrison} garrison per sun to coordinate."
            )
            return []

        # Sort targets by garrison (weakest first).
        targets.sort(key=lambda t: t.garrison)

        # Assign each ready sun to a different target, pairing nearest sun to each target.
        actions: list[Action] = []
        assigned_targets: list[SunView] = []
        remaining_suns = list(ready_suns)

        for target in targets:
            if not remaining_suns:
                break

            # Pick the nearest ready sun to this target.
            nearest_sun = min(
                remaining_suns,
                key=lambda s: s.position.distance_to(target.position),
            )
            available = nearest_sun.garrison - self._reserve
            remaining_suns.remove(nearest_sun)
            if available > 0:
                actions.append(SendUnits(nearest_sun.id, target.id, available))
                assigned_targets.append(target)

        if assigned_targets:
            target_ids = ", ".join(str(t.id) for t in assigned_targets)
            self._intent = (
                f"Coordinated strike on {len(assigned_targets)} targets (suns {target_ids})."
            )
        else:
            self._intent = "Ready suns don't have enough to send. Waiting."

        return actions
