"""Training loop orchestrator — runs evolutionary optimisation.

Usage from CLI:
    clauralux train --population 50 --generations 100 --workers 4
"""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

# Suppress pygame's startup banner in worker processes.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from dataclasses import dataclass
from pathlib import Path

from clauralux.bots.base import Bot
from clauralux.bots.evolved import EvolvedBot
from clauralux.bots.neural import NeuralBot
from clauralux.bots.noisy import NoisyWrapper
from clauralux.bots.registry import training_opponents_with_weights
from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import FLAVOURS, generate_map
from clauralux.engine.maps import two_player_simple
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId

from .evolution import (
    Individual,
    create_next_generation,
    evaluate_fitness,
)
from .genome import (
    PHASE_NAMES,
    TRANSITION_SPECS,
    default_genome,
    genome_to_phase_dicts,
    load_genome,
    neural_load_genome,
    neural_random_genome,
    neural_save_genome,
    random_genome,
    save_genome,
)

# Opponent pool is derived from the central registry, excluding passive and evolved.
OPPONENT_BOTS_WITH_WEIGHTS: list[tuple[type[Bot], float]] = training_opponents_with_weights()


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Configuration for an evolutionary training run."""

    population_size: int = 80
    generations: int = 200
    games_per_eval: int = 40
    workers: int = 0  # 0 = use all available CPUs
    elite_count: int = 5
    sigma_frac: float = 0.05
    sigma_decay: float = 0.995
    mutation_prob: float = 0.2
    output_path: str = "data/evolved_weights.json"
    from_scratch: bool = False
    self_play: bool = False  # only train against other evolved bots
    neural: bool = False  # use neural net bot instead of phase-based evolved
    seed: int = 42
    hall_of_fame_interval: int = 5  # save best genome every N generations
    stagnation_limit: int = 15  # reset sigma after N gens without improvement
    stagnation_inject: float = 0.2  # fraction of population replaced with random on reset


_MAP_FLAVOUR_NAMES = list(FLAVOURS.keys())


def _evaluate_individual(
    args: tuple[list[float], int, int, list[list[float]], bool, list[list[float]], bool],
) -> float:
    """Evaluate a single individual. Designed to be called via ProcessPoolExecutor.

    Args is a tuple of (genome, games_per_eval, rng_seed, hall_of_fame_genomes,
    self_play, peer_genomes, neural).
    """
    genome, games_per_eval, rng_seed, hall_of_fame, self_play, peers, neural = args

    config = GameConfig(max_ticks=10_000)

    def bot_factory(pid: PlayerId) -> Bot:
        if neural:
            return NeuralBot(genome=genome)
        return EvolvedBot(genome=genome)

    def _make_opponent(cls: type[Bot], seed: int) -> Callable[[PlayerId], Bot]:
        def factory(pid: PlayerId) -> Bot:
            return NoisyWrapper(cls(), drop_prob=0.1, seed=seed)

        return factory

    opponents: list[Callable[[PlayerId], Bot]] = []
    opponent_weights: list[float] = []

    if not self_play:
        for i, (cls, weight) in enumerate(OPPONENT_BOTS_WITH_WEIGHTS):
            opponents.append(_make_opponent(cls, rng_seed + i))
            opponent_weights.append(weight)

    # Play against hall-of-fame bots (previous best genomes).
    bot_cls: type[Bot] = NeuralBot if neural else EvolvedBot
    for hof_genome in hall_of_fame:
        g = hof_genome  # capture for closure

        def _hof_factory(pid: PlayerId, g: list[float] = g, cls: type[Bot] = bot_cls) -> Bot:
            return cls(genome=g)  # type: ignore[call-arg]

        opponents.append(_hof_factory)
        opponent_weights.append(1.0)

    # In self-play mode, also play against peers from the current population.
    for peer_genome in peers:
        g = peer_genome

        def _peer_factory(pid: PlayerId, g: list[float] = g, cls: type[Bot] = bot_cls) -> Bot:
            return cls(genome=g)  # type: ignore[call-arg]

        opponents.append(_peer_factory)
        opponent_weights.append(1.0)

    # Use all map flavours plus the fixed map, with seed variation.
    def _make_map(flavour: str, seed: int) -> Callable[[GameConfig], GameState]:
        def factory(cfg: GameConfig) -> GameState:
            return generate_map(cfg, flavour, 2, seed=seed)

        return factory

    maps: list[Callable[[GameConfig], GameState]] = [
        two_player_simple,
        *(_make_map(f, rng_seed + i) for i, f in enumerate(_MAP_FLAVOUR_NAMES)),
    ]

    return evaluate_fitness(
        bot_factory=bot_factory,
        opponents=opponents,
        maps=maps,
        config=config,
        games_per_eval=games_per_eval,
        rng_seed=rng_seed,
        opponent_weights=opponent_weights,
    )


def train(config: TrainingConfig) -> list[float]:
    """Run the full evolutionary training loop. Returns the best genome."""
    rng = random.Random(config.seed)

    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Helpers based on neural mode.
    def _make_default() -> list[float]:
        return neural_random_genome(rng) if config.neural else default_genome()

    def _make_random() -> list[float]:
        return neural_random_genome(rng) if config.neural else random_genome(rng)

    def _load_weights(p: Path) -> list[float]:
        return neural_load_genome(p) if config.neural else load_genome(p)

    def _save_weights(genome: list[float], p: Path) -> None:
        if config.neural:
            neural_save_genome(genome, p)
        else:
            save_genome(genome, p)

    # Seed population with existing trained weights if available.
    population: list[Individual] = []
    prior_best: Individual | None = None
    if not config.from_scratch:
        try:
            existing = _load_weights(output_path)
            population.append(Individual(genome=existing))
            prior_best = Individual(genome=list(existing), fitness=0.0)
            print(f"Loaded existing weights from {output_path} — seeding population.")
        except (FileNotFoundError, ValueError):
            population.append(Individual(genome=_make_default()))
    else:
        print("Starting from scratch — ignoring existing weights.")
        population.append(Individual(genome=_make_default()))

    for _ in range(config.population_size - len(population)):
        population.append(Individual(genome=_make_random()))

    best_ever: Individual | None = None
    sigma = config.sigma_frac
    stagnation_count = 0

    # Hall of fame: best genomes from previous generations.
    # Starts with the prior best from disk (if any).
    hall_of_fame: list[list[float]] = []
    if prior_best is not None:
        hall_of_fame.append(list(prior_best.genome))

    num_workers = config.workers or os.cpu_count() or 4
    print(
        f"Training: pop={config.population_size}, "
        f"gens={config.generations}, "
        f"games/eval={config.games_per_eval}, "
        f"workers={num_workers}"
    )
    if config.self_play:
        print("Mode: self-play (evolved vs evolved only)")
    print(f"Output: {output_path}")
    print("=" * 60)

    executor = ProcessPoolExecutor(max_workers=num_workers) if num_workers > 1 else None

    try:
        for gen in range(config.generations):
            gen_start = time.monotonic()

            # Build evaluation tasks.
            # In self-play mode, each individual plays against a sample of
            # peers (other genomes in the population, excluding itself).
            tasks = []
            for idx, ind in enumerate(population):
                peers: list[list[float]] = (
                    [p.genome for j, p in enumerate(population) if j != idx]
                    if config.self_play
                    else []
                )
                # Note: ProcessPoolExecutor pickles hall_of_fame per task, so each
                # worker gets an immutable snapshot. No lock needed.
                tasks.append(
                    (
                        ind.genome,
                        config.games_per_eval,
                        rng.randint(0, 2**31),
                        hall_of_fame,
                        config.self_play,
                        peers,
                        config.neural,
                    )
                )

            # Evaluate fitness in parallel.
            if executor is not None:
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
                stagnation_count = 0
                # Capture the prior best's evaluated fitness after gen 1.
                if prior_best is not None and prior_best.fitness == 0.0:
                    prior_best.fitness = population[0].fitness
                # Only save if we actually beat whatever was on disk.
                if prior_best is None or best_ever.fitness > prior_best.fitness:
                    _save_weights(best_ever.genome, output_path)
            else:
                stagnation_count += 1

            # Add to hall of fame at regular intervals.
            if (gen + 1) % config.hall_of_fame_interval == 0:
                hall_of_fame.append(list(gen_best.genome))
                # Cap HOF size to avoid quadratic training cost.
                max_hof = 15
                if len(hall_of_fame) > max_hof:
                    hall_of_fame.pop(0)

            elapsed = time.monotonic() - gen_start

            # Progress output.
            print(
                f"Gen {gen + 1:3d}/{config.generations} | "
                f"best={gen_best.fitness:.3f} avg={avg_fitness:.3f} "
                f"all-time={best_ever.fitness:.3f} | "
                f"sigma={sigma:.4f} | "
                f"hof={len(hall_of_fame)} | "
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

            # Stagnation reset: if no improvement for N generations,
            # reset sigma and inject random individuals to escape local optima.
            if stagnation_count >= config.stagnation_limit:
                sigma = config.sigma_frac
                num_inject = max(1, int(len(population) * config.stagnation_inject))
                # Replace the worst individuals with fresh random genomes.
                ranked = sorted(population, key=lambda ind: ind.fitness, reverse=True)
                for i in range(num_inject):
                    ranked[-(i + 1)] = Individual(genome=random_genome(rng))
                population = ranked
                stagnation_count = 0
                print(
                    f"  ** Stagnation reset: sigma→{sigma:.4f}, "
                    f"injected {num_inject} random individuals"
                )
    finally:
        if executor is not None:
            executor.shutdown(wait=False)

    # Final save and summary.
    assert best_ever is not None
    if prior_best is None or best_ever.fitness > prior_best.fitness:
        _save_weights(best_ever.genome, output_path)
        print("=" * 60)
        print(f"Training complete! Best fitness: {best_ever.fitness:.3f}")
        print(f"Weights saved to: {output_path}")
    else:
        print("=" * 60)
        print(
            f"Training complete! Best fitness: {best_ever.fitness:.3f} "
            f"(did not beat prior best {prior_best.fitness:.3f} — keeping existing weights)"
        )
    if config.neural:
        print(f"\nNeural genome: {len(best_ever.genome)} weights")
    else:
        phases, transitions = genome_to_phase_dicts(best_ever.genome)
        print("\nBest parameters:")
        for i, phase_dict in enumerate(phases):
            print(f"  [{PHASE_NAMES[i]}]")
            for name, value in phase_dict.items():
                print(f"    {name}: {value:.3f}")
        for i, spec in enumerate(TRANSITION_SPECS):
            print(f"  {spec.name}: {transitions[i]:.0f}")

    return best_ever.genome
