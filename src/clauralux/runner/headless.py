from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId
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
        self._config = config
        self._game = Game(config, initial_state)
        self._bots = bots
        self._recorder = recorder

    @property
    def game(self) -> Game:
        return self._game

    def run(self) -> GameResult:
        """Run the game to completion and return the result."""
        game = self._game
        cfg = self._config

        # Notify bots of game start.
        for player_id, bot in self._bots.items():
            bot.on_game_start(game.get_view(player_id))

        while not game.is_over:
            # Poll bots on decision ticks.
            if game.state.tick % cfg.decision_interval == 0:
                for player_id, bot in self._bots.items():
                    if player_id not in game.state.eliminated:
                        view = game.get_view(player_id)
                        actions = bot.decide(view)
                        if self._recorder is not None:
                            self._recorder.record_actions(game.state.tick, player_id, actions)
                        game.apply_actions(player_id, actions)
            game.tick()

        # Notify bots of game end.
        for player_id, bot in self._bots.items():
            bot.on_game_end(game.get_view(player_id))

        winner = game.state.winner
        return GameResult(
            winner=winner,
            ticks=game.state.tick,
            eliminated=frozenset(game.state.eliminated),
            is_draw=winner == NEUTRAL,
        )
