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
from clauralux.runner.headless import HeadlessRunner

from .genome import PARAM_SPECS, clamp_genome

# Type alias: creates a Bot for a given player ID.
BotFactory = Callable[[PlayerId], Bot]

# Type alias: creates initial game state from config.
MapFactory = Callable[[GameConfig], GameState]


@dataclass(slots=True)
class Individual:
    """A candidate solution in the population."""

    genome: list[float]
    fitness: float = 0.0


def evaluate_fitness(
    bot_factory: BotFactory,
    opponents: Sequence[BotFactory],
    maps: Sequence[MapFactory],
    config: GameConfig,
    games_per_eval: int,
    rng_seed: int | None = None,
) -> float:
    """Evaluate a bot's fitness by playing games against various opponents.

    Returns a score in [0, 1] where 1.0 = won every game.
    Draws count as 0.3 to mildly reward survival.
    """
    if not opponents or not maps:
        return 0.0

    total_score = 0.0
    games_played = 0

    for i in range(games_per_eval):
        opponent = opponents[i % len(opponents)]
        map_factory = maps[i % len(maps)]

        state = map_factory(config)
        bots = {
            PlayerId(1): bot_factory(PlayerId(1)),
            PlayerId(2): opponent(PlayerId(2)),
        }
        runner = HeadlessRunner(config, state, bots)
        result = runner.run()
        games_played += 1

        if result.winner == PlayerId(1):
            total_score += 1.0
        elif result.is_draw:
            total_score += 0.3

    return total_score / max(games_played, 1)


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

    sigma_frac is the fraction of each parameter's range used as sigma.
    """
    result = list(genome)
    for i, spec in enumerate(PARAM_SPECS):
        if rng.random() < mutation_prob:
            sigma = (spec.hi - spec.lo) * sigma_frac
            result[i] += rng.gauss(0.0, sigma)
    return clamp_genome(result)


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
