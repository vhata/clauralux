"""Training loop orchestrator — runs evolutionary optimisation.

Usage from CLI:
    clauralux train --population 50 --generations 100 --workers 4
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.base import Bot
from clauralux.bots.evolved import EvolvedBot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.opportunist import OpportunistBot
from clauralux.bots.random_bot import RandomBot
from clauralux.bots.rush import RushBot
from clauralux.bots.sniper import SniperBot
from clauralux.bots.turtle import TurtleBot
from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import generate_map
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId

from .evolution import (
    Individual,
    create_next_generation,
    evaluate_fitness,
)
from .genome import (
    default_genome,
    genome_to_dict,
    load_genome,
    random_genome,
    save_genome,
)

# All opponent bot classes for fitness evaluation.
OPPONENT_BOTS: list[type[Bot]] = [
    AggressiveBot,
    ExpanderBot,
    OpportunistBot,
    RandomBot,
    RushBot,
    SniperBot,
    TurtleBot,
]


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Configuration for an evolutionary training run."""

    population_size: int = 50
    generations: int = 100
    games_per_eval: int = 20
    workers: int = 4
    elite_count: int = 5
    sigma_frac: float = 0.05
    sigma_decay: float = 0.995
    mutation_prob: float = 0.2
    output_path: str = "data/evolved_weights.json"
    seed: int = 42


def _evaluate_individual(args: tuple[list[float], int, int]) -> float:
    """Evaluate a single individual. Designed to be called via ProcessPoolExecutor.

    Args is a tuple of (genome, games_per_eval, rng_seed) to be picklable.
    """
    genome, games_per_eval, rng_seed = args

    config = GameConfig(max_ticks=10_000)

    def bot_factory(pid: PlayerId) -> Bot:
        return EvolvedBot(genome=genome)

    opponents = [lambda pid, cls=cls: cls() for cls in OPPONENT_BOTS]

    maps = [
        two_player_simple,
        lambda cfg: generate_map(cfg, "default", 2, seed=rng_seed),
        lambda cfg: generate_map(cfg, "dense", 2, seed=rng_seed + 1),
    ]

    return evaluate_fitness(
        bot_factory=bot_factory,
        opponents=opponents,
        maps=maps,
        config=config,
        games_per_eval=games_per_eval,
        rng_seed=rng_seed,
    )


def train(config: TrainingConfig) -> list[float]:
    """Run the full evolutionary training loop. Returns the best genome."""
    rng = random.Random(config.seed)

    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Seed population with existing trained weights if available.
    population: list[Individual] = []
    prior_best: Individual | None = None
    try:
        existing = load_genome(output_path)
        population.append(Individual(genome=existing))
        prior_best = Individual(genome=list(existing), fitness=0.0)
        print(f"Loaded existing weights from {output_path} — seeding population.")
    except FileNotFoundError:
        population.append(Individual(genome=default_genome()))

    for _ in range(config.population_size - len(population)):
        population.append(Individual(genome=random_genome(rng)))

    best_ever: Individual | None = None
    sigma = config.sigma_frac

    print(
        f"Training: pop={config.population_size}, "
        f"gens={config.generations}, "
        f"games/eval={config.games_per_eval}, "
        f"workers={config.workers}"
    )
    print(f"Output: {output_path}")
    print("=" * 60)

    for gen in range(config.generations):
        gen_start = time.monotonic()

        # Build evaluation tasks.
        tasks = [(ind.genome, config.games_per_eval, rng.randint(0, 2**31)) for ind in population]

        # Evaluate fitness in parallel.
        if config.workers > 1:
            with ProcessPoolExecutor(max_workers=config.workers) as executor:
                fitnesses = list(executor.map(_evaluate_individual, tasks))
        else:
            fitnesses = [_evaluate_individual(t) for t in tasks]

        for ind, fit in zip(population, fitnesses, strict=True):
            ind.fitness = fit

        # Find generation best.
        gen_best = max(population, key=lambda ind: ind.fitness)
        avg_fitness = sum(ind.fitness for ind in population) / len(population)

        if best_ever is None or gen_best.fitness > best_ever.fitness:
            best_ever = Individual(
                genome=list(gen_best.genome),
                fitness=gen_best.fitness,
            )
            # Capture the prior best's evaluated fitness after gen 1.
            if prior_best is not None and prior_best.fitness == 0.0:
                prior_best.fitness = population[0].fitness
            # Only save if we actually beat whatever was on disk.
            if prior_best is None or best_ever.fitness > prior_best.fitness:
                save_genome(best_ever.genome, output_path)

        elapsed = time.monotonic() - gen_start

        # Progress output.
        print(
            f"Gen {gen + 1:3d}/{config.generations} | "
            f"best={gen_best.fitness:.3f} avg={avg_fitness:.3f} "
            f"all-time={best_ever.fitness:.3f} | "
            f"sigma={sigma:.4f} | "
            f"{elapsed:.1f}s"
        )

        # Create next generation.
        population = create_next_generation(
            population=population,
            elite_count=config.elite_count,
            sigma_frac=sigma,
            mutation_prob=config.mutation_prob,
            rng=rng,
        )
        sigma *= config.sigma_decay

    # Final save and summary.
    assert best_ever is not None
    if prior_best is None or best_ever.fitness > prior_best.fitness:
        save_genome(best_ever.genome, output_path)
        print("=" * 60)
        print(f"Training complete! Best fitness: {best_ever.fitness:.3f}")
        print(f"Weights saved to: {output_path}")
    else:
        print("=" * 60)
        print(
            f"Training complete! Best fitness: {best_ever.fitness:.3f} "
            f"(did not beat prior best {prior_best.fitness:.3f} — keeping existing weights)"
        )
    print("\nBest parameters:")
    for name, value in genome_to_dict(best_ever.genome).items():
        print(f"  {name}: {value:.3f}")

    return best_ever.genome
