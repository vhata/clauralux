from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.types import SunId
from clauralux.engine.view import GameView, SunView

from .base import Bot


class ExpanderBot(Bot):
    """Prioritises capturing neutral suns, then upgrades, then attacks enemies.

    Improved: responds to threats, upgrades earlier, attacks more decisively.
    """

    def __init__(
        self,
        reserve: int = 3,
        upgrade_threshold: int = 20,
        act_interval: int = 25,
    ) -> None:
        super().__init__()
        self._reserve = reserve
        self._upgrade_threshold = upgrade_threshold
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns left."
            return []

        # Phase 0: respond to incoming threats.
        threat_actions = self._handle_threats(view, my_suns)
        if threat_actions:
            return threat_actions

        # Phase 1: upgrade suns that can afford it.
        for sun in my_suns:
            if sun.level < view.config.max_sun_level and sun.garrison >= self._upgrade_threshold:
                self._intent = (
                    f"Sun {sun.id} has {sun.garrison} garrison — upgrading to level"
                    f" {sun.level + 1}."
                )
                return [UpgradeSun(sun.id)]

        # Phase 2: capture the nearest neutral.
        neutrals = view.neutral_suns()
        if neutrals:
            target = self._nearest_target(my_suns, neutrals)
            if target is not None:
                actions = self._send_from_all(my_suns, target, force_ratio=0.8)
                if actions:
                    self._intent = (
                        f"Expanding: nearest neutral is Sun {target.id}"
                        f" (garrison {target.garrison})."
                    )
                    return actions

        # Phase 3: attack weakest enemy.
        enemies = view.enemy_suns()
        if enemies:
            target = min(enemies, key=lambda s: s.garrison)
            actions = self._send_from_all(my_suns, target, force_ratio=1.2)
            if actions:
                self._intent = (
                    f"No neutrals left. Attacking weakest enemy Sun {target.id}"
                    f" (P{target.owner}, garrison {target.garrison})."
                )
                return actions

        self._intent = "Building up forces."
        return []

    def _handle_threats(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Reinforce suns that have incoming enemy units."""
        my_sun_ids = {s.id: s for s in my_suns}
        # Find the most threatened sun.
        threats: dict[SunId, int] = {}
        for group in view.enemy_unit_groups():
            if group.target_sun_id in my_sun_ids:
                threats[group.target_sun_id] = threats.get(group.target_sun_id, 0) + group.count

        if not threats:
            return []

        # Find sun with worst deficit (incoming - garrison).
        worst_id = max(threats, key=lambda sid: threats[sid] - my_sun_ids[sid].garrison)
        deficit = threats[worst_id] - my_sun_ids[worst_id].garrison
        if deficit <= 0:
            return []  # Garrison can handle it.

        # Send reinforcements from the safest sun with most garrison.
        safe_suns = [
            s
            for s in my_suns
            if s.id != worst_id and s.id not in threats and s.garrison > self._reserve + 2
        ]
        if not safe_suns:
            return []
        donor = max(safe_suns, key=lambda s: s.garrison)
        send = min(donor.garrison - self._reserve, deficit + 2)
        if send > 0:
            self._intent = f"Threat! Sun {worst_id} under attack. Reinforcing from Sun {donor.id}."
            return [SendUnits(donor.id, worst_id, send)]
        return []

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

    def _send_from_all(
        self, my_suns: tuple[SunView, ...], target: SunView, force_ratio: float = 1.0
    ) -> list[Action]:
        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
        if total_available < target.garrison * force_ratio:
            return []

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
