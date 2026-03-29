from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class ExpanderBot(Bot):
    """Prioritises capturing neutral suns, then upgrades, then attacks enemies."""

    def __init__(
        self,
        reserve: int = 3,
        upgrade_threshold: int = 30,
        act_interval: int = 40,
    ) -> None:
        self._reserve = reserve
        self._upgrade_threshold = upgrade_threshold
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        actions: list[Action] = []
        my_suns = view.my_suns()

        # Phase 1: try to upgrade suns with lots of garrison.
        for sun in my_suns:
            if sun.level < view.config.max_sun_level and sun.garrison >= self._upgrade_threshold:
                actions.append(UpgradeSun(sun.id))
                return actions  # one action at a time, keep it simple

        # Phase 2: capture the nearest neutral.
        neutrals = view.neutral_suns()
        if neutrals:
            target = self._nearest_target(my_suns, neutrals)
            if target is not None:
                return self._send_from_all(my_suns, target)

        # Phase 3: attack weakest enemy.
        enemies = view.enemy_suns()
        if enemies:
            target = min(enemies, key=lambda s: s.garrison)
            return self._send_from_all(my_suns, target)

        return actions

    def _nearest_target(
        self,
        my_suns: tuple[SunView, ...],
        targets: tuple[SunView, ...],
    ) -> SunView | None:
        if not my_suns or not targets:
            return None
        best = None
        best_dist = float("inf")
        for mine in my_suns:
            for t in targets:
                d = mine.position.distance_to(t.position)
                if d < best_dist:
                    best_dist = d
                    best = t
        return best

    def _send_from_all(self, my_suns: tuple[SunView, ...], target: SunView) -> list[Action]:
        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
