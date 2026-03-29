from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId

from .headless import GameResult, HeadlessRunner


@dataclass(frozen=True, slots=True)
class TournamentResult:
    """Aggregate results from a tournament of multiple games."""

    total_games: int
    wins: dict[PlayerId, int]
    draws: int
    avg_ticks: float
    results: tuple[GameResult, ...]

    def win_rate(self, player_id: PlayerId) -> float:
        if self.total_games == 0:
            return 0.0
        return self.wins.get(player_id, 0) / self.total_games


# A factory that creates bots for a given player ID.
BotFactory = Callable[[PlayerId], Bot]

# A factory that creates initial game state.
MapFactory = Callable[[GameConfig], GameState]


def run_tournament(
    config: GameConfig,
    map_factory: MapFactory,
    bot_factories: dict[PlayerId, BotFactory],
    num_games: int,
) -> TournamentResult:
    """Run multiple games and aggregate results."""
    results: list[GameResult] = []
    wins: Counter[PlayerId] = Counter()
    draws = 0
    total_ticks = 0

    for _ in range(num_games):
        state = map_factory(config)
        bots = {pid: factory(pid) for pid, factory in bot_factories.items()}
        runner = HeadlessRunner(config, state, bots)
        result = runner.run()
        results.append(result)
        total_ticks += result.ticks

        if result.is_draw:
            draws += 1
        elif result.winner is not None:
            wins[result.winner] += 1

    avg_ticks = total_ticks / max(num_games, 1)

    return TournamentResult(
        total_games=num_games,
        wins=dict(wins),
        draws=draws,
        avg_ticks=avg_ticks,
        results=tuple(results),
    )
