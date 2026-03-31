from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class TurtleBot(Bot):
    """Upgrades everything to max, builds huge garrisons, then overwhelms.

    Improved: grabs nearby neutrals for economy, attacks once level 2+.
    """

    def __init__(self, attack_threshold: int = 40, act_interval: int = 30) -> None:
        super().__init__()
        self._attack_threshold = attack_threshold
        self._act_interval = act_interval
        self._reserve = 5

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns left."
            return []

        # Phase 1: upgrade any sun that can afford it.
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

        # Phase 2: grab nearby neutrals (early expansion to build economy).
        neutrals = view.neutral_suns()
        avg_level = sum(s.level for s in my_suns) / len(my_suns)
        if neutrals and avg_level < 2:
            # Only grab easy neutrals — ones we can take without overcommitting.
            target = self._nearest_weak_neutral(my_suns, neutrals)
            if target is not None:
                total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
                if total_available > target.garrison:
                    self._intent = (
                        f"Grabbing nearby neutral Sun {target.id}"
                        f" (garrison {target.garrison}) for economy."
                    )
                    return self._send_from_all(my_suns, target)

        # Phase 3: attack once average level >= 2 and garrison is high enough.
        if avg_level < 2:
            self._intent = f"Turtling: avg level {avg_level:.1f}, waiting for upgrades."
            return []

        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns are mine."
            return []

        target = min(targets, key=lambda s: s.garrison)
        total_garrison = sum(s.garrison for s in my_suns)

        if total_garrison < self._attack_threshold:
            self._intent = (
                f"Building up: {int(total_garrison)} garrison, need {self._attack_threshold}."
            )
            return []

        owner_label = f"P{target.owner}" if target.owner else "neutral"
        self._intent = (
            f"Upgraded (avg L{avg_level:.1f}), {int(total_garrison)} garrison."
            f" Crushing Sun {target.id} ({owner_label}, garrison {target.garrison})."
        )
        return self._send_from_all(my_suns, target)

    def _nearest_weak_neutral(
        self, my_suns: tuple[SunView, ...], neutrals: tuple[SunView, ...]
    ) -> SunView | None:
        """Find nearest neutral with garrison <= 15 (easy to take)."""
        best = None
        best_dist = float("inf")
        for mine in my_suns:
            for n in neutrals:
                if n.garrison > 15:
                    continue
                d = mine.position.distance_to(n.position)
                if d < best_dist:
                    best_dist = d
                    best = n
        return best

    def _send_from_all(self, my_suns: tuple[SunView, ...], target: SunView) -> list[Action]:
        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
