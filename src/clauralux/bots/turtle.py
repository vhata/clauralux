from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView

from .base import Bot


class TurtleBot(Bot):
    """Upgrades everything to max, builds huge garrisons, then overwhelms."""

    def __init__(self, attack_threshold: int = 40, act_interval: int = 50) -> None:
        super().__init__()
        self._attack_threshold = attack_threshold
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()

        # Priority 1: upgrade any sun that isn't max level.
        for sun in my_suns:
            if sun.level < view.config.max_sun_level:
                cost_idx = sun.level - 1
                if cost_idx < len(view.config.upgrade_costs):
                    cost = view.config.upgrade_costs[cost_idx]
                    if sun.garrison >= cost:
                        self._intent = (
                            f"Fortifying: upgrading Sun {sun.id} to level {sun.level + 1}"
                            f" (garrison {sun.garrison})."
                        )
                        return [UpgradeSun(sun.id)]

        # Priority 2: if all suns are max level and garrison is high, attack.
        all_maxed = all(s.level >= view.config.max_sun_level for s in my_suns)
        total_garrison = sum(s.garrison for s in my_suns)

        if not all_maxed:
            self._intent = f"Turtling: waiting for upgrades. Total garrison: {int(total_garrison)}."
            return []

        # Pick weakest non-friendly sun, but only if we have overwhelming force.
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns are mine. Victory is inevitable."
            return []

        target = min(targets, key=lambda s: s.garrison)

        if total_garrison < self._attack_threshold:
            self._intent = (
                f"Building up: {int(total_garrison)} garrison,"
                f" need {self._attack_threshold} before attacking."
            )
            return []

        owner_label = f"P{target.owner}" if target.owner else "neutral"
        self._intent = (
            f"Fully upgraded, {int(total_garrison)} garrison."
            f" Crushing Sun {target.id} ({owner_label}, garrison {target.garrison})."
        )

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - 5  # keep a decent reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
