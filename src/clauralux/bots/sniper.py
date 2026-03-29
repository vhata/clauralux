from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.types import SunId
from clauralux.engine.view import GameView

from .base import Bot


class SniperBot(Bot):
    """Ignores neutrals. Targets enemy suns to eliminate players."""

    def __init__(self, reserve: int = 3, act_interval: int = 60) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        enemies = view.enemy_suns()

        if not enemies:
            # No enemies left — mop up neutrals.
            neutrals = view.neutral_suns()
            if not neutrals:
                self._intent = "All enemies eliminated. Map is mine."
                return []
            target = min(neutrals, key=lambda s: s.garrison)
            self._intent = (
                f"No enemies left. Mopping up neutral Sun {target.id} (garrison {target.garrison})."
            )
            return self._send_all(my_suns, target.id)

        # Find the enemy player closest to elimination:
        # fewest total units (garrison + in-flight).
        enemy_strength: dict[int, int] = {}
        for s in view.suns:
            if s.owner != view.my_id and s.owner:
                enemy_strength.setdefault(s.owner, 0)
                enemy_strength[s.owner] += s.garrison
        for g in view.unit_groups:
            if g.owner != view.my_id and g.owner:
                enemy_strength.setdefault(g.owner, 0)
                enemy_strength[g.owner] += g.count

        if not enemy_strength:
            self._intent = "No enemies detected."
            return []

        # Target the weakest player's weakest sun.
        weakest_player = min(enemy_strength, key=lambda p: enemy_strength[p])
        player_suns = [s for s in enemies if s.owner == weakest_player]

        if not player_suns:
            self._intent = f"P{weakest_player} has no suns but units in flight. Waiting."
            return []

        target = min(player_suns, key=lambda s: s.garrison)

        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
        if total_available <= target.garrison:
            self._intent = (
                f"Targeting P{weakest_player} (weakest, {enemy_strength[weakest_player]} total)."
                f" Building up — need more than {target.garrison} to take Sun {target.id}."
            )
            return []

        self._intent = (
            f"Sniping P{weakest_player}'s Sun {target.id} (garrison {target.garrison})."
            f" Going for the elimination."
        )
        return self._send_all(my_suns, target.id)

    def _send_all(self, my_suns: tuple, target_id: SunId) -> list[Action]:
        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target_id, available))
        return actions
