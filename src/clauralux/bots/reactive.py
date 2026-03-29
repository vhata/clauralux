from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView, SunView

from .base import Bot


class ReactiveBot(Bot):
    """Defensive bot that reinforces threatened suns and only attacks with overwhelming force."""

    def __init__(self, reserve: int = 5, act_interval: int = 25) -> None:
        super().__init__()
        self._reserve = reserve
        self._act_interval = act_interval

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. Nothing to defend."
            return []

        # Check for incoming threats to our suns.
        threat_actions = self._handle_threats(view, my_suns)
        if threat_actions:
            return threat_actions

        # No threats — look for safe attack opportunities.
        return self._handle_attack(view, my_suns)

    def _incoming_threat(self, view: GameView, sun: SunView) -> int:
        """Count enemy units heading toward one of our suns."""
        total = 0
        for group in view.enemy_unit_groups():
            if group.target_sun_id == sun.id:
                total += group.count
        return total

    def _handle_threats(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Reinforce the most threatened sun from the safest sun."""
        threats: list[tuple[SunView, int]] = []
        for sun in my_suns:
            incoming = self._incoming_threat(view, sun)
            if incoming > 0:
                deficit = incoming - sun.garrison
                threats.append((sun, deficit))

        if not threats:
            return []

        # Reinforce the sun with the worst deficit.
        threats.sort(key=lambda x: x[1], reverse=True)
        threatened_sun, deficit = threats[0]

        if deficit <= 0:
            self._intent = (
                f"Sun {threatened_sun.id} has incoming but garrison can handle it. Holding."
            )
            return []

        # Find the safest sun to send reinforcements from.
        safe_suns = [
            s for s in my_suns if s.id != threatened_sun.id and self._incoming_threat(view, s) == 0
        ]
        if not safe_suns:
            safe_suns = [s for s in my_suns if s.id != threatened_sun.id]

        if not safe_suns:
            self._intent = f"Sun {threatened_sun.id} under threat but no suns to reinforce from."
            return []

        # Send from the sun with the most garrison.
        source = max(safe_suns, key=lambda s: s.garrison)
        send_amount = min(source.garrison - self._reserve, deficit + 5)
        if send_amount <= 0:
            self._intent = (
                f"Sun {threatened_sun.id} needs reinforcement but no spare units to send."
            )
            return []

        self._intent = (
            f"Reinforcing Sun {threatened_sun.id} ({deficit} unit deficit) from Sun {source.id}."
        )
        return [SendUnits(source.id, threatened_sun.id, send_amount)]

    def _handle_attack(self, view: GameView, my_suns: tuple[SunView, ...]) -> list[Action]:
        """Only attack when we have overwhelming force and no threats."""
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns mine. Holding position."
            return []

        total_available = sum(max(0, s.garrison - self._reserve) for s in my_suns)
        target = min(targets, key=lambda s: s.garrison)

        # Only attack with 2x advantage.
        if total_available < target.garrison * 2:
            self._intent = (
                f"Weakest target Sun {target.id} has {target.garrison} garrison."
                f" Need 2x advantage ({total_available} available). Holding."
            )
            return []

        owner_label = f"P{target.owner}" if target.owner else "neutral"
        self._intent = (
            f"No threats detected. Overwhelming Sun {target.id}"
            f" ({owner_label}, {target.garrison} garrison)"
            f" with {total_available} units."
        )

        actions: list[Action] = []
        for sun in my_suns:
            available = sun.garrison - self._reserve
            if available > 0:
                actions.append(SendUnits(sun.id, target.id, available))
        return actions
