"""A bot that replays pre-recorded actions."""

from __future__ import annotations

from clauralux.bots.base import Bot
from clauralux.engine.actions import Action
from clauralux.engine.view import GameView


class ReplayBot(Bot):
    """Plays back recorded actions from a replay file."""

    def __init__(
        self,
        action_schedule: list[tuple[int, list[Action]]],
        bot_name: str = "replay",
    ) -> None:
        super().__init__()
        # Build a tick -> actions lookup for O(1) access.
        self._actions_by_tick: dict[int, list[Action]] = {}
        for tick, actions in action_schedule:
            self._actions_by_tick[tick] = actions
        self._bot_name = bot_name

    def decide(self, view: GameView) -> list[Action]:
        actions = self._actions_by_tick.get(view.tick, [])
        if actions:
            self._intent = f"Replay ({self._bot_name}): {len(actions)} action(s)"
        else:
            self._intent = f"Replay ({self._bot_name}): waiting"
        return actions
