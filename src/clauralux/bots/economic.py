from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class EconomicBot(Bot):
    """Upgrades aggressively, then targets the opponent's highest-level suns."""

    def __init__(self, reserve: int = 3, act_interval: int = 35) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. Economy collapsed."
            return []

        # Phase 1: Grab nearest neutral if any exist.
        neutral_action = self._grab_neutral(view, my_suns)
        if neutral_action:
            return neutral_action

        # Phase 2: Upgrade any sun that can afford it.
        upgrade_action = self._upgrade(view, my_suns)
        if upgrade_action:
            return upgrade_action

        # Phase 3: Target enemy's highest-level sun to deny production.
        return self._deny_economy(view, my_suns)

    def _grab_neutral(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Grab the nearest neutral sun if we can afford it."""
        neutrals = list(view.neutral_suns())
        if not neutrals:
            return []

        # Find the nearest neutral to any of our suns.
        best_pair: tuple[SunView, SunView, float] | None = None
        for mine in my_suns:
            for neutral in neutrals:
                d = mine.position.distance_to(neutral.position)
                if best_pair is None or d < best_pair[2]:
                    best_pair = (mine, neutral, d)

        if best_pair is None:
            return []

        source, target, _dist = best_pair
        needed = target.garrison + 2
        available = source.garrison - self._reserve
        if available < needed:
            return []

        self._intent = f"Expanding — grabbing neutral Sun {target.id}."
        return [SendUnits(source.id, target.id, needed)]

    def _upgrade(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Upgrade the lowest-level sun that can afford it."""
        upgradeable = [s for s in my_suns if s.level < view.config.max_sun_level]
        if not upgradeable:
            return []

        # Upgrade the one with the lowest level first (most production gain).
        upgradeable.sort(key=lambda s: (s.level, -s.garrison))
        for sun in upgradeable:
            cost_index = sun.level - 1
            costs = view.config.upgrade_costs
            if cost_index < len(costs) and sun.garrison >= costs[cost_index]:
                self._intent = (
                    f"Upgrading Sun {sun.id} from level {sun.level} — investing in production."
                )
                return [UpgradeSun(sun.id)]

        return []

    def _deny_economy(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Target the enemy's highest-level sun to deny their production."""
        enemy_suns = list(view.enemy_suns())
        if not enemy_suns:
            # Fall back to neutrals.
            targets = [s for s in view.suns if s.owner != view.my_id]
            if not targets:
                self._intent = "All suns mine. Economy dominant."
                return []
            enemy_suns = targets

        # Sort by level descending — target the most valuable sun.
        enemy_suns.sort(key=lambda s: (-s.level, s.garrison))
        target = enemy_suns[0]

        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
        if total_available <= target.garrison:
            self._intent = (
                f"Eyeing level-{target.level} Sun {target.id}"
                f" ({target.garrison} garrison) but need more force."
            )
            return []

        owner_label = f"P{target.owner}" if target.owner else "neutral"
        self._intent = (
            f"Denying production — targeting level-{target.level} Sun {target.id} ({owner_label})."
        )

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
