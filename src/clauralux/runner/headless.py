from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.replay.recorder import GameRecorder


@dataclass(frozen=True, slots=True)
class GameResult:
    """Result of a completed game."""

    winner: PlayerId | None  # None should not happen; NEUTRAL = draw
    ticks: int
    eliminated: frozenset[PlayerId]
    is_draw: bool


class HeadlessRunner:
    """Runs a game with no rendering, as fast as possible."""

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bots: Mapping[PlayerId, Bot],
        recorder: GameRecorder | None = None,
    ) -> None:
        from clauralux.runner.base import BaseRunner

        self._base = BaseRunner(config, initial_state, bots, recorder)

    @property
    def game(self) -> Game:
        return self._base.game

    def run(self) -> GameResult:
        """Run the game to completion and return the result."""
        self._base._notify_start()

        while not self._base.game.is_over:
            self._base._run_decision_tick()
            self._base.game.tick()

        self._base._notify_end()
        return self._base._build_result()
