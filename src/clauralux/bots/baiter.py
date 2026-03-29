from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView, SunView

from .base import Bot


class BaiterBot(Bot):
    """Sends small bait attacks to draw out defenders, then hits the weakened suns."""

    def __init__(self, reserve: int = 3, act_interval: int = 40) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval
        self._bait_target_id: int | None = None
        self._bait_tick: int = -1000

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not my_suns or not targets:
            self._intent = "Nothing to bait." if not targets else "No suns left."
            return []

        # If we baited recently, look for the weakened sun to hit.
        if self._bait_target_id is not None and view.tick - self._bait_tick < 200:
            return self._follow_up(view, my_suns, targets)

        # Otherwise, send bait.
        return self._send_bait(view, my_suns, targets)

    def _send_bait(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        targets: list[SunView],
    ) -> list[Action]:
        """Send a tiny force at a distant target to draw a reaction."""
        # Pick a distant enemy sun as the bait target.
        enemy_suns = [t for t in targets if t.owner != 0]
        bait_candidates = enemy_suns if enemy_suns else targets

        if not bait_candidates:
            return []

        # Find the source sun with the most units.
        source = max(my_suns, key=lambda s: s.garrison)
        if source.garrison < self._reserve + 2:
            self._intent = "Not enough units to bait with."
            return []

        # Pick a target that's far away (maximises reaction time for us).
        bait_target = max(
            bait_candidates,
            key=lambda t: source.position.distance_to(t.position),
        )

        self._bait_target_id = bait_target.id
        self._bait_tick = view.tick

        owner_label = f"P{bait_target.owner}" if bait_target.owner else "neutral"
        self._intent = (
            f"Baiting Sun {bait_target.id} ({owner_label}) with 2 units. Watching for a reaction."
        )
        return [SendUnits(source.id, bait_target.id, 2)]

    def _follow_up(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        targets: list[SunView],
    ) -> list[Action]:
        """After baiting, find the weakest sun near the bait target's owner and strike."""
        # Find which player owns the bait target.
        bait_sun = None
        for t in targets:
            if t.id == self._bait_target_id:
                bait_sun = t
                break

        if bait_sun is None:
            # Bait target was captured or doesn't exist — reset.
            self._bait_target_id = None
            return []

        bait_owner = bait_sun.owner

        # Look for a different sun owned by the same player that might be weakened.
        same_owner = [t for t in targets if t.owner == bait_owner and t.id != self._bait_target_id]

        strike_target = min(same_owner, key=lambda s: s.garrison) if same_owner else bait_sun

        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
        if total_available <= strike_target.garrison:
            self._intent = (
                f"Bait sent to Sun {self._bait_target_id}."
                f" Waiting for force to strike Sun {strike_target.id}"
                f" ({strike_target.garrison} garrison)."
            )
            return []

        # Reset bait state and commit the strike.
        self._bait_target_id = None

        owner_label = f"P{strike_target.owner}" if strike_target.owner else "neutral"
        self._intent = (
            f"Follow-up strike! Hitting weakened Sun {strike_target.id}"
            f" ({owner_label}, {strike_target.garrison} garrison)."
        )

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, strike_target.id, available))
        return actions
