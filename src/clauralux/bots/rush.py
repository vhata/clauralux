from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class RushBot(Bot):
    """Sends units constantly with minimal reserve. Pure early pressure.

    Improved: basic viability check, mid-game upgrades, prefers weak targets.
    """

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

        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "Everything is mine already."
            return []

        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)

        # Mid-game transition: if no easy enemy targets, grab neutrals or upgrade.
        easy_targets = [t for t in targets if t.garrison < total_available * 0.8]
        if not easy_targets:
            # Grab nearest neutral first — don't just sit idle.
            neutrals = view.neutral_suns()
            if neutrals:
                nearest_neutral = min(
                    neutrals,
                    key=lambda t: min(m.position.distance_to(t.position) for m in my_suns),
                )
                if total_available > nearest_neutral.garrison:
                    self._intent = f"No easy fights. Grabbing neutral Sun {nearest_neutral.id}."
                    return self._send_from_all(my_suns, nearest_neutral)

            for sun in my_suns:
                if sun.level < view.config.max_sun_level:
                    cost_idx = sun.level - 1
                    if cost_idx < len(view.config.upgrade_costs):
                        cost = view.config.upgrade_costs[cost_idx]
                        if sun.garrison >= cost:
                            self._intent = (
                                f"No easy targets. Upgrading Sun {sun.id} to level {sun.level + 1}."
                            )
                            return [UpgradeSun(sun.id)]

        # Pick the best target: nearest sun that we can actually take.
        best_target: SunView | None = None
        best_score = float("inf")

        for mine in my_suns:
            for t in targets:
                d = mine.position.distance_to(t.position)
                # Skip targets we can't possibly take.
                if t.garrison > total_available * 1.5:
                    continue
                # Score: distance + garrison penalty (prefer close AND weak).
                score = d + t.garrison * 5
                if score < best_score:
                    best_score = score
                    best_target = t

        # Fallback to pure nearest if all targets are too strong.
        if best_target is None:
            best_target = min(
                targets,
                key=lambda t: min(m.position.distance_to(t.position) for m in my_suns),
            )

        # Don't throw units away: require at least 60% of target garrison.
        if total_available < best_target.garrison * 0.6:
            self._intent = (
                f"Building up — {int(total_available)} available vs"
                f" {best_target.garrison} garrison at target."
            )
            return []

        # Send from all suns.
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
                f"RUSH! {total_sent} units at Sun {best_target.id}"
                f" ({owner_label}, garrison {best_target.garrison})."
            )

        return actions

    def _send_from_all(self, my_suns: tuple[SunView, ...], target: SunView) -> list[Action]:
        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
