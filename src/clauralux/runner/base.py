from __future__ import annotations

from collections.abc import Mapping

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId
from clauralux.replay.recorder import GameRecorder
from clauralux.runner.headless import GameResult, GameSnapshot, PlayerSnapshot


class BaseRunner:
    """Shared game-loop logic for headless and visual runners."""

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bots: Mapping[PlayerId, Bot],
        recorder: GameRecorder | None = None,
        snapshot_interval: int = 0,
    ) -> None:
        self._config = config
        self._game = Game(config, initial_state)
        self._bots = bots
        self._recorder = recorder
        self._snapshot_interval = snapshot_interval
        self._snapshots: list[GameSnapshot] = []

    @property
    def game(self) -> Game:
        return self._game

    def _notify_start(self) -> None:
        for player_id, bot in self._bots.items():
            bot.on_game_start(self._game.get_view(player_id))

    def _notify_end(self) -> None:
        for player_id, bot in self._bots.items():
            bot.on_game_end(self._game.get_view(player_id))

    def _run_decision_tick(self) -> None:
        """Poll all non-eliminated bots and apply their actions."""
        game = self._game
        if game.state.tick % self._config.decision_interval != 0:
            return
        for player_id, bot in self._bots.items():
            if player_id not in game.state.eliminated:
                view = game.get_view(player_id)
                actions = bot.decide(view)
                if self._recorder is not None:
                    self._recorder.record_actions(game.state.tick, player_id, actions)
                game.apply_actions(player_id, actions)

    def _maybe_snapshot(self) -> None:
        """Capture a game state snapshot if the interval has elapsed."""
        if self._snapshot_interval <= 0:
            return
        tick = self._game.state.tick
        if tick % self._snapshot_interval != 0:
            return
        state = self._game.state
        players: dict[PlayerId, PlayerSnapshot] = {}
        for pid in state.players:
            if pid in state.eliminated:
                players[pid] = PlayerSnapshot(suns=0, garrison=0, in_flight=0, level_sum=0)
                continue
            suns = [s for s in state.suns.values() if s.owner == pid]
            garrison = int(sum(s.garrison for s in suns))
            in_flight = sum(g.count for g in state.unit_groups if g.owner == pid)
            level_sum = sum(s.level for s in suns)
            players[pid] = PlayerSnapshot(
                suns=len(suns), garrison=garrison, in_flight=in_flight, level_sum=level_sum
            )
        self._snapshots.append(GameSnapshot(tick=tick, players=players))

    def _build_result(self) -> GameResult:
        game = self._game
        winner = game.state.winner
        return GameResult(
            winner=winner,
            ticks=game.state.tick,
            eliminated=frozenset(game.state.eliminated),
            is_draw=winner == NEUTRAL,
            snapshots=tuple(self._snapshots),
        )
