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

from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import FLAVOURS, generate_map
from clauralux.engine.maps import two_player_simple
from clauralux.engine.state import GameState

from .evolution import (
    Individual,
    create_next_generation,
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
    args: tuple[list[float], int, int, list[list[float]], bool, list[list[float]], bool, float],
) -> float:
    """Evaluate a single individual entirely in Rust.

    Args is a tuple of (genome, games_per_eval, rng_seed, hall_of_fame_genomes,
    self_play, peer_genomes, neural, curriculum_phase).
    """
    genome, games_per_eval, rng_seed, hall_of_fame, self_play, peers, neural, curriculum_phase = (
        args
    )

    from clauralux.bots.registry import training_opponent_names_with_weights

    config = GameConfig(max_ticks=10_000)

    # Build opponent list: named bots + genome-based opponents.
    # Named bots (hand-crafted) — filtered by curriculum.
    named_opponents: list[tuple[str, float]] = []
    genome_opponents: list[tuple[list[float], float]] = []

    if not self_play:
        difficulty_cap = 0.8 + curriculum_phase * 0.6
        for name, weight in training_opponent_names_with_weights():
            if weight <= difficulty_cap:
                named_opponents.append((name, weight))

    # Hall-of-fame + peers (genome-based).
    for hof_genome in hall_of_fame:
        genome_opponents.append((hof_genome, 1.0))
    for peer_genome in peers:
        genome_opponents.append((peer_genome, 1.0))

    # Build map factories.
    def _make_map(flavour: str, seed: int) -> Callable[[GameConfig], GameState]:
        def factory(cfg: GameConfig) -> GameState:
            return generate_map(cfg, flavour, 2, seed=seed)

        return factory

    maps: list[Callable[[GameConfig], GameState]] = [
        two_player_simple,
        *(_make_map(f, rng_seed + i) for i, f in enumerate(_MAP_FLAVOUR_NAMES)),
    ]

    all_opponents = len(named_opponents) + len(genome_opponents)
    if all_opponents == 0:
        return 0.0

    return _evaluate_all_rust(
        genome,
        named_opponents,
        genome_opponents,
        maps,
        config,
        games_per_eval,
        rng_seed,
        neural,
    )


def _evaluate_all_rust(
    genome: list[float],
    named_opponents: list[tuple[str, float]],
    genome_opponents: list[tuple[list[float], float]],
    maps: list[Callable[[GameConfig], GameState]],
    config: GameConfig,
    games_per_eval: int,
    rng_seed: int,
    neural: bool = False,
) -> float:
    """Evaluate genome against all opponents using Rust runners."""
    from clauralux._engine import (
        run_neural_training_game,
        run_training_game,
        run_training_game_vs_bot,
    )

    max_ticks = config.max_ticks or 10_000
    run_genome_game = run_neural_training_game if neural else run_training_game

    # Interleave all opponents for game assignment.
    all_opps: list[tuple[str | None, list[float] | None, float]] = []
    for name, weight in named_opponents:
        all_opps.append((name, None, weight))
    for g, weight in genome_opponents:
        all_opps.append((None, g, weight))

    if not all_opps:
        return 0.0

    opp_scores: dict[int, list[float]] = {}

    for i in range(games_per_eval):
        opp_idx = i % len(all_opps)
        opp_name, opp_genome, weight = all_opps[opp_idx]
        map_factory = maps[i % len(maps)]

        state = map_factory(config)
        sun_ids, sun_xs, sun_ys, sun_owners, sun_garrisons, sun_levels = [], [], [], [], [], []
        for sid, sun in state.suns.items():
            sun_ids.append(int(sid))
            sun_xs.append(float(sun.position.x))
            sun_ys.append(float(sun.position.y))
            sun_owners.append(int(sun.owner))
            sun_garrisons.append(float(sun.garrison))
            sun_levels.append(int(sun.level))

        if opp_name is not None:
            # Named bot opponent.
            result = run_training_game_vs_bot(
                config,
                sun_ids,
                sun_xs,
                sun_ys,
                sun_owners,
                sun_garrisons,
                sun_levels,
                [1, 2],
                genome,
                opp_name,
                neural,
                rng_seed + i,
            )
        else:
            # Genome-based opponent.
            assert opp_genome is not None
            result = run_genome_game(
                config,
                sun_ids,
                sun_xs,
                sun_ys,
                sun_owners,
                sun_garrisons,
                sun_levels,
                [1, 2],
                genome,
                opp_genome,
            )

        # Score game.
        my_id = 1
        if result.is_draw:
            base = 0.15
            speed_bonus = 0.0
        elif result.winner == my_id:
            base = 1.0
            speed_bonus = max(0.0, 0.2 * (1.0 - result.ticks / max_ticks))
        else:
            base = 0.0
            speed_bonus = 0.0

        territory_bonus = 0.1 * (result.p1_suns / max(result.total_suns, 1))
        score = base + speed_bonus + territory_bonus
        if opp_idx not in opp_scores:
            opp_scores[opp_idx] = []
        opp_scores[opp_idx].append(score)

    # Weighted average + worst-case.
    total_score = 0.0
    total_weight = 0.0
    for opp_idx, scores in opp_scores.items():
        w = all_opps[opp_idx][2]
        for s in scores:
            total_score += w * s
            total_weight += w
    avg = total_score / max(total_weight, 1.0)

    worst = min(
        (sum(scores) / len(scores) for scores in opp_scores.values()),
        default=0.0,
    )

    return 0.5 * avg + 0.5 * worst


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
            curriculum_phase = gen / max(config.generations - 1, 1)
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
                        curriculum_phase,
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
                    # Keep a timestamped backup so good weights are never lost.
                    backup = output_path.with_suffix(
                        f".backup-{time.strftime('%Y%m%d-%H%M%S')}.json"
                    )
                    _save_weights(best_ever.genome, backup)
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
                    ranked[-(i + 1)] = Individual(genome=_make_random())
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
