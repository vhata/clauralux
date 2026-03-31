"""Evolutionary operators and fitness evaluation.

These functions operate on raw list[float] genomes — they don't know or care
whether the floats represent heuristic weights or neural network parameters.
This makes the entire module reusable for Phase 2 (neural nets).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import GameResult, HeadlessRunner

from .genome import ALL_SPECS, NEURAL_WEIGHT_RANGE, clamp_genome

# Type alias: creates a Bot for a given player ID.
BotFactory = Callable[[PlayerId], Bot]

# Type alias: creates initial game state from config.
MapFactory = Callable[[GameConfig], GameState]


@dataclass(slots=True)
class Individual:
    """A candidate solution in the population."""

    genome: list[float]
    fitness: float = 0.0


def _score_game(
    result: GameResult,
    final_state: GameState,
    my_id: PlayerId,
    max_ticks: int,
) -> float:
    """Score a single game with richer signal than plain win/draw/loss.

    Components:
    - Base: 1.0 for win, 0.15 for draw, 0.0 for loss
    - Speed bonus: up to 0.2 for winning quickly (normalised by max_ticks)
    - Territory bonus: up to 0.1 for controlling more suns at game end
    """
    if result.winner == my_id:
        base = 1.0
        speed_bonus = 0.2 * (1.0 - result.ticks / max_ticks)
    else:
        base = 0.15 if result.is_draw else 0.0
        speed_bonus = 0.0

    # Count suns owned at end of game.
    my_suns = sum(1 for sun in final_state.suns.values() if sun.owner == my_id)
    total_suns = max(len(final_state.suns), 1)
    territory_bonus = 0.1 * (my_suns / total_suns)

    return base + speed_bonus + territory_bonus


def evaluate_fitness(
    bot_factory: BotFactory,
    opponents: Sequence[BotFactory],
    maps: Sequence[MapFactory],
    config: GameConfig,
    games_per_eval: int,
    rng_seed: int | None = None,
    opponent_weights: Sequence[float] | None = None,
    worst_case_weight: float = 0.5,
) -> float:
    """Evaluate a bot's fitness by playing games against various opponents.

    Returns a score where higher is better. Uses a richer signal than plain
    win/loss: rewards decisive victories and territorial control.

    Fitness = (1 - worst_case_weight) * weighted_avg + worst_case_weight * worst_opponent.
    This prevents the optimizer from sacrificing any single matchup.
    """
    if not opponents or not maps:
        return 0.0

    weights = opponent_weights or [1.0] * len(opponents)
    max_ticks = config.max_ticks or 10_000

    # Track per-opponent scores for worst-case calculation.
    opp_scores: dict[int, list[float]] = {}

    for i in range(games_per_eval):
        opponent_idx = i % len(opponents)
        opponent = opponents[opponent_idx]
        map_factory = maps[i % len(maps)]

        state = map_factory(config)
        my_id = PlayerId(1)
        bots = {
            my_id: bot_factory(my_id),
            PlayerId(2): opponent(PlayerId(2)),
        }
        runner = HeadlessRunner(config, state, bots)
        result = runner.run()

        score = _score_game(result, runner.game.state, my_id, max_ticks)
        if opponent_idx not in opp_scores:
            opp_scores[opponent_idx] = []
        opp_scores[opponent_idx].append(score)

    # Weighted average across all games.
    total_score = 0.0
    total_weight = 0.0
    for opp_idx, scores in opp_scores.items():
        w = weights[opp_idx]
        for s in scores:
            total_score += w * s
            total_weight += w
    avg = total_score / max(total_weight, 1.0)

    # Worst per-opponent average (unweighted — we care about the weakest matchup).
    worst = min(
        (sum(scores) / len(scores) for scores in opp_scores.values()),
        default=0.0,
    )

    return (1.0 - worst_case_weight) * avg + worst_case_weight * worst


def tournament_select(
    population: list[Individual],
    k: int,
    rng: random.Random,
) -> Individual:
    """Select the fittest of k randomly chosen individuals."""
    candidates = rng.sample(population, min(k, len(population)))
    return max(candidates, key=lambda ind: ind.fitness)


def uniform_crossover(
    a: list[float],
    b: list[float],
    rng: random.Random,
) -> list[float]:
    """Each gene comes from parent A or B with equal probability."""
    return [rng.choice([va, vb]) for va, vb in zip(a, b, strict=True)]


def gaussian_mutate(
    genome: list[float],
    sigma_frac: float,
    mutation_prob: float,
    rng: random.Random,
) -> list[float]:
    """Apply Gaussian noise to each gene with per-gene probability.

    For heuristic genomes (phase-based), sigma_frac is the fraction of each
    parameter's range. For neural genomes (longer than ALL_SPECS), uses a
    fixed weight range.
    """
    result = list(genome)
    if len(genome) <= len(ALL_SPECS):
        # Phase-based genome: per-parameter ranges.
        for i, spec in enumerate(ALL_SPECS):
            if rng.random() < mutation_prob:
                sigma = (spec.hi - spec.lo) * sigma_frac
                result[i] += rng.gauss(0.0, sigma)
        return clamp_genome(result)
    else:
        # Neural genome: uniform sigma across all weights.
        sigma = NEURAL_WEIGHT_RANGE * 2 * sigma_frac
        for i in range(len(genome)):
            if rng.random() < mutation_prob:
                result[i] += rng.gauss(0.0, sigma)
        return [max(-NEURAL_WEIGHT_RANGE, min(NEURAL_WEIGHT_RANGE, v)) for v in result]


def create_next_generation(
    population: list[Individual],
    elite_count: int,
    sigma_frac: float,
    mutation_prob: float,
    rng: random.Random,
) -> list[Individual]:
    """Produce the next generation via elitism, selection, crossover, mutation."""
    pop_size = len(population)
    # Sort by fitness descending.
    ranked = sorted(population, key=lambda ind: ind.fitness, reverse=True)

    next_gen: list[Individual] = []

    # Elitism: carry top individuals unchanged.
    for ind in ranked[:elite_count]:
        next_gen.append(Individual(genome=list(ind.genome)))

    # Fill remaining slots.
    while len(next_gen) < pop_size:
        parent_a = tournament_select(population, k=3, rng=rng)
        parent_b = tournament_select(population, k=3, rng=rng)
        child_genome = uniform_crossover(parent_a.genome, parent_b.genome, rng)
        child_genome = gaussian_mutate(child_genome, sigma_frac, mutation_prob, rng)
        next_gen.append(Individual(genome=child_genome))

    return next_gen[:pop_size]
