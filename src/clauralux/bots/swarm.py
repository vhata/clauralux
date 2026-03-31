from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.view import GameView, SunView

from .base import Bot


class SwarmBot(Bot):
    """Many small attacks from every sun. Death by a thousand cuts.

    Improved: scales group size, concentrates on weak targets, upgrades when idle.
    """

    def __init__(self, min_send: int = 3, act_interval: int = 15) -> None:
        super().__init__()
        self._min_send = min_send
        self._act_interval = act_interval
        self._reserve = 2

    def decide(self, view: GameView) -> list[Action]:
        if view.tick % self._act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. Swarmed out."
            return []

        targets: list[SunView] = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "Everything is mine. The swarm has consumed all."
            return []

        # Find the weakest target.
        weakest = min(targets, key=lambda t: t.garrison)

        # Scale send size: at least min_send, up to 1/3 of weakest target garrison.
        send_size = max(self._min_send, int(weakest.garrison * 0.35))

        available_suns: list[SunView] = [
            s for s in my_suns if s.garrison > send_size + self._reserve
        ]

        # If no suns have enough to attack, upgrade instead.
        if not available_suns:
            for sun in my_suns:
                if sun.level < view.config.max_sun_level:
                    cost_idx = sun.level - 1
                    if cost_idx < len(view.config.upgrade_costs):
                        cost = view.config.upgrade_costs[cost_idx]
                        if sun.garrison >= cost:
                            self._intent = f"No attack force. Upgrading Sun {sun.id}."
                            return [UpgradeSun(sun.id)]
            self._intent = "Building up swarm reserves."
            return []

        # Concentration mode: if weakest target is killable, focus fire.
        total_sendable = len(available_suns) * send_size
        if weakest.garrison <= total_sendable * 0.7:
            # Send from the nearest suns — enough to overwhelm.
            needed = int(weakest.garrison * 1.3) + 1
            nearest = sorted(
                available_suns,
                key=lambda s: s.position.distance_to(weakest.position),
            )
            actions: list[Action] = []
            sent = 0
            for sun in nearest:
                amount = min(send_size, sun.garrison - self._reserve)
                if amount > 0:
                    actions.append(SendUnits(sun.id, weakest.id, amount))
                    sent += amount
                if sent >= needed:
                    break
            if actions:
                self._intent = (
                    f"Concentrating — {len(actions)} groups ({sent} units) at"
                    f" Sun {weakest.id} (garrison {weakest.garrison})."
                )
                return actions

        # Spread mode: each sun attacks its nearest weak target.
        actions = []
        weak_targets: list[SunView] = [t for t in targets if t.garrison <= send_size * 4]
        if not weak_targets:
            weak_targets = list(targets)

        for sun in available_suns:
            tgt: SunView = min(weak_targets, key=lambda t: sun.position.distance_to(t.position))
            amount = min(send_size, sun.garrison - self._reserve)
            if amount >= self._min_send:
                actions.append(SendUnits(sun.id, tgt.id, amount))

        if actions:
            self._intent = f"Swarming — {len(actions)} groups launched."
        else:
            self._intent = "Building reserves."

        return actions
