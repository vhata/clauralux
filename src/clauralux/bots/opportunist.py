from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class OpportunistBot(Bot):
    """Watches for weakened suns and swoops in. Expands opportunistically."""

    def __init__(self, reserve: int = 3, act_interval: int = 30) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)

        if total_available <= 0:
            self._intent = "No units to spare. Biding time."
            return []

        # Look for easy pickings: non-friendly suns with very low garrison.
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns mine. Nothing to do."
            return []

        # Score targets: lower garrison = more appealing, closer = more appealing.
        scored = self._score_targets(my_suns, targets)

        if not scored:
            self._intent = "No good opportunities. Waiting."
            return []

        _best_score, best_target = scored[0]

        # Only strike if it's a genuine opportunity (low garrison relative to our force).
        if best_target.garrison >= total_available * 0.8:
            # Nothing easy enough — try upgrading instead.
            for sun in my_suns:
                if sun.level < view.config.max_sun_level and sun.garrison >= 20:
                    self._intent = f"No easy targets. Upgrading Sun {sun.id} while we wait."
                    return [UpgradeSun(sun.id)]

            self._intent = (
                f"Best target Sun {best_target.id} has {best_target.garrison} garrison."
                f" Too risky with {total_available} available. Waiting for an opening."
            )
            return []

        owner_label = f"P{best_target.owner}" if best_target.owner else "neutral"
        self._intent = (
            f"Opportunity! Sun {best_target.id} ({owner_label})"
            f" only has {best_target.garrison} garrison. Pouncing."
        )

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, best_target.id, available))
        return actions

    def _score_targets(
        self,
        my_suns: tuple[SunView, ...],
        targets: list[SunView],
    ) -> list[tuple[float, SunView]]:
        """Score targets by garrison (lower=better) and distance (closer=better)."""
        scored: list[tuple[float, SunView]] = []
        for t in targets:
            min_dist = min(
                (s.position.distance_to(t.position) for s in my_suns),
                default=float("inf"),
            )
            # Score: garrison weighted heavily, distance as tiebreaker.
            score = t.garrison + min_dist * 0.05
            scored.append((score, t))
        scored.sort(key=lambda x: x[0])
        return scored
