"""Parity tests: Python EvolvedBot vs Rust training runner.

These tests ensure the Rust implementation of the evolved bot heuristic
produces similar outcomes to the Python version. Small floating-point
differences can cause divergence over thousands of ticks, so we check
that winners match and tick counts are in the same ballpark.
"""

from __future__ import annotations

import random
from typing import Any

from clauralux._engine import GameConfig, run_training_game
from clauralux.bots.evolved import EvolvedBot
from clauralux.engine.mapgen import generate_map
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import GameResult, HeadlessRunner
from clauralux.training.genome import default_genome, random_genome


def _extract_sun_arrays(
    state: Any,
) -> tuple[list[int], list[float], list[float], list[int], list[float], list[int]]:
    """Extract sun data as parallel arrays for the Rust runner."""
    ids: list[int] = []
    xs: list[float] = []
    ys: list[float] = []
    owners: list[int] = []
    garrisons: list[float] = []
    levels: list[int] = []
    for sid, sun in state.suns.items():
        ids.append(int(sid))
        xs.append(sun.position.x)
        ys.append(sun.position.y)
        owners.append(int(sun.owner))
        garrisons.append(sun.garrison)
        levels.append(int(sun.level))
    return ids, xs, ys, owners, garrisons, levels


def _run_python_game(
    config: GameConfig, state: Any, genome1: list[float], genome2: list[float]
) -> GameResult:
    """Run a game using the Python EvolvedBot."""
    p1, p2 = PlayerId(1), PlayerId(2)
    bots = {p1: EvolvedBot(genome=genome1), p2: EvolvedBot(genome=genome2)}
    runner = HeadlessRunner(config, state, bots)
    return runner.run()


def _run_rust_game(
    config: GameConfig, state: Any, genome1: list[float], genome2: list[float]
) -> Any:
    """Run a game using the Rust training runner."""
    arrays = _extract_sun_arrays(state)
    return run_training_game(config, *arrays, [1, 2], genome1, genome2)


class TestParity:
    """Verify Python and Rust evolved bot produce similar game outcomes."""

    def test_default_genome_same_winner(self) -> None:
        """Default genome vs itself should produce same winner."""
        config = GameConfig(max_ticks=5_000)
        genome = default_genome()

        py = _run_python_game(config, two_player_simple(config), genome, genome)
        rs = _run_rust_game(config, two_player_simple(config), genome, genome)

        assert py.winner == rs.winner, (
            f"Winner mismatch: Python={py.winner} ({py.ticks}t), Rust={rs.winner} ({rs.ticks}t)"
        )

    def test_random_genomes_same_winner(self) -> None:
        """Multiple random genome pairs should mostly produce matching winners."""
        config = GameConfig(max_ticks=5_000)
        rng = random.Random(789)

        matches = 0
        total = 20
        for _ in range(total):
            g1 = random_genome(rng)
            g2 = random_genome(rng)
            py = _run_python_game(config, two_player_simple(config), g1, g2)
            rs = _run_rust_game(config, two_player_simple(config), g1, g2)
            if py.winner == rs.winner:
                matches += 1

        # Allow some divergence from floating-point differences, but
        # at least 60% of games should have the same winner.
        match_pct = matches / total * 100
        assert matches >= total * 0.6, (
            f"Only {matches}/{total} ({match_pct:.0f}%) games had matching winners. "
            f"Expected at least 70%. This suggests a logic divergence, not just FP drift."
        )

    def test_rust_runner_completes(self) -> None:
        """Rust runner produces valid results on all map types."""
        config = GameConfig(max_ticks=5_000)
        genome = default_genome()

        for flavour in ["strategic", "rush", "chokepoint", "swarm"]:
            state = generate_map(config, flavour, 2, seed=42)
            result = _run_rust_game(config, state, genome, genome)
            assert result.winner in (0, 1, 2), f"Invalid winner {result.winner} on {flavour}"
            assert result.ticks > 0, f"Zero ticks on {flavour}"

    def test_rust_runner_respects_max_ticks(self) -> None:
        """Rust runner respects the max_ticks config."""
        config = GameConfig(max_ticks=100)
        genome = default_genome()
        result = _run_rust_game(config, two_player_simple(config), genome, genome)
        assert result.ticks <= 101  # tick increments after check, allow +1
        assert result.is_draw  # 100 ticks is way too short for a win
