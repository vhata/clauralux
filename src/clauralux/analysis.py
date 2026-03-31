"""Bot matchup analysis — runs all-vs-all tournaments and diagnoses weaknesses.

Produces a rich JSON report with per-matchup win rates and telemetry-based
diagnostics showing when and why each bot falls behind.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from clauralux.bots.base import Bot
from clauralux.bots.registry import BOT_REGISTRY
from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import FLAVOURS, generate_map
from clauralux.engine.maps import two_player_simple
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import GameResult
from clauralux.runner.tournament import BotFactory, MapFactory, run_tournament

# Bots excluded from analysis (not real strategies).
_EXCLUDED = {"passive", "human", "evolved", "neural"}

# Snapshot every 500 ticks for telemetry.
_SNAPSHOT_INTERVAL = 500


def _make_bot_factory(name: str) -> BotFactory:
    def factory(_pid: PlayerId) -> Bot:
        from clauralux.bots.registry import BOT_REGISTRY as reg

        return reg[name]()

    return factory


def _map_factories() -> list[tuple[str, MapFactory]]:
    """All maps used for analysis — fixed + one of each flavour."""
    factories: list[tuple[str, MapFactory]] = [("simple", two_player_simple)]
    for flavour in FLAVOURS:

        def _make(f: str) -> MapFactory:
            def factory(cfg: GameConfig) -> GameState:
                return generate_map(cfg, f, 2)

            return factory

        factories.append((flavour, _make(flavour)))
    return factories


@dataclass
class MatchupResult:
    """Detailed results of one bot vs another across all maps."""

    bot_a: str
    bot_b: str
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    total_games: int = 0
    avg_ticks: float = 0.0
    # Telemetry: average snapshot values for the losing side at game midpoint.
    a_mid_suns: float = 0.0
    a_mid_garrison: float = 0.0
    b_mid_suns: float = 0.0
    b_mid_garrison: float = 0.0

    @property
    def a_win_pct(self) -> float:
        return self.a_wins / max(self.total_games, 1) * 100

    @property
    def b_win_pct(self) -> float:
        return self.b_wins / max(self.total_games, 1) * 100


def _extract_midpoint_stats(
    results: tuple[GameResult, ...],
    pid: PlayerId,
) -> tuple[float, float]:
    """Average sun count and garrison at the game midpoint for a player."""
    sun_vals: list[float] = []
    garrison_vals: list[float] = []
    for r in results:
        if not r.snapshots:
            continue
        mid_idx = len(r.snapshots) // 2
        snap = r.snapshots[mid_idx]
        ps = snap.players.get(pid)
        if ps:
            sun_vals.append(ps.suns)
            garrison_vals.append(ps.garrison)
    if not sun_vals:
        return 0.0, 0.0
    return sum(sun_vals) / len(sun_vals), sum(garrison_vals) / len(garrison_vals)


def run_matchup_matrix(
    games_per_matchup: int = 20,
    bot_names: list[str] | None = None,
) -> list[MatchupResult]:
    """Run every bot vs every other bot across all maps.

    Returns a list of MatchupResult with win rates and midpoint telemetry.
    """
    if bot_names is None:
        bot_names = [n for n in BOT_REGISTRY if n not in _EXCLUDED]

    config = GameConfig(max_ticks=10_000)
    maps = _map_factories()
    games_per_map = max(1, games_per_matchup // len(maps))

    matchups: list[MatchupResult] = []

    for i, name_a in enumerate(bot_names):
        for name_b in bot_names[i + 1 :]:
            mr = MatchupResult(bot_a=name_a, bot_b=name_b)
            all_results: list[GameResult] = []

            for _map_name, map_factory in maps:
                result = run_tournament(
                    config=config,
                    map_factory=map_factory,
                    bot_factories={
                        PlayerId(1): _make_bot_factory(name_a),
                        PlayerId(2): _make_bot_factory(name_b),
                    },
                    num_games=games_per_map,
                    rotate_positions=True,
                    snapshot_interval=_SNAPSHOT_INTERVAL,
                )
                mr.a_wins += result.wins.get(PlayerId(1), 0)
                mr.b_wins += result.wins.get(PlayerId(2), 0)
                mr.draws += result.draws
                mr.total_games += result.total_games
                all_results.extend(result.results)

            if all_results:
                mr.avg_ticks = sum(r.ticks for r in all_results) / len(all_results)

            mr.a_mid_suns, mr.a_mid_garrison = _extract_midpoint_stats(
                tuple(all_results), PlayerId(1)
            )
            mr.b_mid_suns, mr.b_mid_garrison = _extract_midpoint_stats(
                tuple(all_results), PlayerId(2)
            )
            matchups.append(mr)

    return matchups


@dataclass
class BotWeakness:
    """A diagnosed weakness for a specific bot."""

    bot: str
    opponent: str
    win_pct: float
    diagnosis: str


def diagnose_weaknesses(matchups: list[MatchupResult]) -> list[BotWeakness]:
    """Analyze matchup results and diagnose why bots lose specific matchups.

    Returns a list of weaknesses sorted by severity (lowest win rate first).
    """
    weaknesses: list[BotWeakness] = []

    for mr in matchups:
        # Check if bot_a is weak against bot_b.
        if mr.a_win_pct < 40 and mr.total_games >= 5:
            diag = _diagnose_one(mr, loser="a")
            weaknesses.append(
                BotWeakness(bot=mr.bot_a, opponent=mr.bot_b, win_pct=mr.a_win_pct, diagnosis=diag)
            )
        # Check if bot_b is weak against bot_a.
        if mr.b_win_pct < 40 and mr.total_games >= 5:
            diag = _diagnose_one(mr, loser="b")
            weaknesses.append(
                BotWeakness(bot=mr.bot_b, opponent=mr.bot_a, win_pct=mr.b_win_pct, diagnosis=diag)
            )

    weaknesses.sort(key=lambda w: w.win_pct)
    return weaknesses


def _diagnose_one(mr: MatchupResult, loser: str) -> str:
    """Generate a diagnosis for why one side loses."""
    if loser == "a":
        loser_suns, loser_garrison = mr.a_mid_suns, mr.a_mid_garrison
        winner_suns, winner_garrison = mr.b_mid_suns, mr.b_mid_garrison
        loser_name, winner_name = mr.bot_a, mr.bot_b
    else:
        loser_suns, loser_garrison = mr.b_mid_suns, mr.b_mid_garrison
        winner_suns, winner_garrison = mr.a_mid_suns, mr.a_mid_garrison
        loser_name, winner_name = mr.bot_b, mr.bot_a

    parts: list[str] = []

    if loser_suns < winner_suns * 0.6:
        parts.append(f"losing territory by midgame ({loser_suns:.1f} vs {winner_suns:.1f} suns)")
    elif loser_suns > winner_suns * 0.9:
        parts.append("territory roughly even at midpoint")

    if loser_garrison < winner_garrison * 0.5:
        parts.append(
            f"garrison deficit at midpoint ({loser_garrison:.0f} vs {winner_garrison:.0f})"
        )

    if loser_suns >= winner_suns * 0.9 and loser_garrison >= winner_garrison * 0.8:
        parts.append("competitive at midpoint but loses in the endgame")

    if not parts:
        parts.append("gradual decline across the game")

    return f"{loser_name} vs {winner_name}: " + "; ".join(parts)


def matchups_to_json(matchups: list[MatchupResult], weaknesses: list[BotWeakness]) -> dict:
    """Convert analysis results to a JSON-serializable dict."""
    # Build win rate matrix.
    bot_names: set[str] = set()
    for mr in matchups:
        bot_names.add(mr.bot_a)
        bot_names.add(mr.bot_b)
    sorted_names = sorted(bot_names)

    matrix: dict[str, dict[str, float]] = {n: {} for n in sorted_names}
    for mr in matchups:
        matrix[mr.bot_a][mr.bot_b] = round(mr.a_win_pct, 1)
        matrix[mr.bot_b][mr.bot_a] = round(mr.b_win_pct, 1)

    return {
        "bots": sorted_names,
        "win_rate_matrix": matrix,
        "matchups": [
            {
                "bot_a": mr.bot_a,
                "bot_b": mr.bot_b,
                "a_wins": mr.a_wins,
                "b_wins": mr.b_wins,
                "draws": mr.draws,
                "total_games": mr.total_games,
                "a_win_pct": round(mr.a_win_pct, 1),
                "b_win_pct": round(mr.b_win_pct, 1),
                "avg_ticks": round(mr.avg_ticks, 0),
                "a_mid_suns": round(mr.a_mid_suns, 2),
                "a_mid_garrison": round(mr.a_mid_garrison, 0),
                "b_mid_suns": round(mr.b_mid_suns, 2),
                "b_mid_garrison": round(mr.b_mid_garrison, 0),
            }
            for mr in matchups
        ],
        "weaknesses": [
            {
                "bot": w.bot,
                "opponent": w.opponent,
                "win_pct": round(w.win_pct, 1),
                "diagnosis": w.diagnosis,
            }
            for w in weaknesses
        ],
    }


def save_analysis(data: dict, path: str | Path) -> None:
    """Save analysis results to JSON."""
    Path(path).write_text(json.dumps(data, indent=2) + "\n")
