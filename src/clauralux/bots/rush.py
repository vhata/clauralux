from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView, SunView

from .base import Bot


class RushBot(Bot):
    """Sends units constantly with minimal reserve. Pure early pressure."""

    def __init__(self, reserve: int = 1, rush_interval: int = 20) -> None:
        super().__init__()
        self._reserve = reserve
        self._rush_interval = rush_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._rush_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. GG."
            return []

        # Find the nearest non-friendly sun to any of our suns.
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "Everything is mine already."
            return []

        best_target: SunView | None = None
        best_dist = float("inf")
        best_source: SunView | None = None

        for mine in my_suns:
            for t in targets:
                d = mine.position.distance_to(t.position)
                if d < best_dist:
                    best_dist = d
                    best_target = t
                    best_source = mine

        if best_target is None or best_source is None:
            return []

        # Send everything we can from all suns at the nearest target.
        actions: list[Action] = []
        total_sent = 0
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, best_target.id, available))
                total_sent += available

        if total_sent > 0:
            owner_label = f"P{best_target.owner}" if best_target.owner else "neutral"
            self._intent = (
                f"RUSH! Throwing {total_sent} units at nearest Sun {best_target.id}"
                f" ({owner_label}). No time to think."
            )
        else:
            self._intent = "Broke. Waiting for just a few more units to throw."

        return actions
