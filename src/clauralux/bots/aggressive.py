from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView

from .base import Bot


class AggressiveBot(Bot):
    """Accumulates units then sends them all at the weakest non-friendly sun."""

    def __init__(self, reserve: int = 2, attack_interval: int = 100) -> None:
        super().__init__()
        self._reserve = reserve
        self._attack_interval = attack_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._attack_interval != 0:
            self._intent = (
                f"Waiting to strike (tick {view.tick % self._attack_interval}"
                f"/{self._attack_interval})."
            )
            return []

        # Consider all non-friendly suns as targets.
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns are mine. Nothing left to conquer."
            return []

        # Pick the weakest target.
        target = min(targets, key=lambda s: s.garrison)

        # Calculate total available units.
        total_available = sum(max(0, sun.garrison - self._reserve) for sun in view.my_suns())

        # Only attack if we can overwhelm the target.
        if total_available <= target.garrison:
            owner_label = f"P{target.owner}" if target.owner else "neutral"
            self._intent = (
                f"Eyeing Sun {target.id} ({owner_label}, garrison {target.garrison}) "
                f"but only have {total_available} available. Building up."
            )
            return []

        owner_label = f"P{target.owner}" if target.owner else "neutral"
        self._intent = (
            f"Sun {target.id} ({owner_label}) has weakest garrison ({target.garrison}). "
            f"Overwhelming with {total_available} units."
        )

        actions: list[Action] = []
        for sun in view.my_suns():
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))

        return actions
