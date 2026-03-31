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
    rotate_positions: bool = False,
) -> TournamentResult:
    """Run multiple games and aggregate results.

    If *rotate_positions* is True, bot-to-player-slot assignments are
    rotated each game so that no bot benefits from a fixed map position.
    Wins are still attributed to the *original* player IDs passed in
    ``bot_factories`` (i.e. the bot identity, not the slot it happened
    to occupy in a given game).
    """
    results: list[GameResult] = []
    wins: Counter[PlayerId] = Counter()
    draws = 0
    total_ticks = 0

    # Canonical ordering of player IDs and their factories.
    canonical_pids = list(bot_factories.keys())
    factories_list = [bot_factories[pid] for pid in canonical_pids]
    n_players = len(canonical_pids)

    for game_idx in range(num_games):
        state = map_factory(config)

        if rotate_positions and n_players > 1:
            # Rotate which factory gets which slot.
            offset = game_idx % n_players
            rotated = factories_list[offset:] + factories_list[:offset]
            slot_to_canonical = {
                canonical_pids[slot]: canonical_pids[(slot + offset) % n_players]
                for slot in range(n_players)
            }
        else:
            rotated = factories_list
            slot_to_canonical = {pid: pid for pid in canonical_pids}

        bots = {canonical_pids[i]: rotated[i](canonical_pids[i]) for i in range(n_players)}
        runner = HeadlessRunner(config, state, bots)
        result = runner.run()
        results.append(result)
        total_ticks += result.ticks

        if result.is_draw:
            draws += 1
        elif result.winner is not None:
            # Map the winning slot back to the canonical bot identity.
            original_pid = slot_to_canonical.get(result.winner, result.winner)
            wins[original_pid] += 1

    avg_ticks = total_ticks / max(num_games, 1)

    return TournamentResult(
        total_games=num_games,
        wins=dict(wins),
        draws=draws,
        avg_ticks=avg_ticks,
        results=tuple(results),
    )
