import random

from clauralux.training.evolution import (
    Individual,
    create_next_generation,
    gaussian_mutate,
    tournament_select,
    uniform_crossover,
)
from clauralux.training.genome import (
    ALL_SPECS,
    NUM_PARAMS,
    default_genome,
    random_genome,
)


class TestCrossover:
    def test_uniform_crossover_length(self) -> None:
        rng = random.Random(42)
        a = default_genome()
        b = random_genome(rng)
        child = uniform_crossover(a, b, rng)
        assert len(child) == NUM_PARAMS

    def test_uniform_crossover_values_from_parents(self) -> None:
        rng = random.Random(42)
        a = [0.0] * NUM_PARAMS
        b = [1.0] * NUM_PARAMS
        child = uniform_crossover(a, b, rng)
        for v in child:
            assert v in (0.0, 1.0)


class TestMutation:
    def test_mutation_preserves_length(self) -> None:
        rng = random.Random(42)
        g = default_genome()
        mutated = gaussian_mutate(g, sigma_frac=0.1, mutation_prob=1.0, rng=rng)
        assert len(mutated) == NUM_PARAMS

    def test_mutation_stays_in_range(self) -> None:
        rng = random.Random(42)
        g = default_genome()
        # High mutation to stress test clamping.
        mutated = gaussian_mutate(g, sigma_frac=1.0, mutation_prob=1.0, rng=rng)
        for p, v in zip(ALL_SPECS, mutated, strict=True):
            assert p.lo <= v <= p.hi, f"{p.name}: {v} not in [{p.lo}, {p.hi}]"

    def test_zero_mutation_prob_no_change(self) -> None:
        rng = random.Random(42)
        g = default_genome()
        mutated = gaussian_mutate(g, sigma_frac=0.1, mutation_prob=0.0, rng=rng)
        assert mutated == g


class TestSelection:
    def test_tournament_select_returns_fittest(self) -> None:
        rng = random.Random(42)
        pop = [
            Individual(genome=default_genome(), fitness=0.1),
            Individual(genome=default_genome(), fitness=0.9),
            Individual(genome=default_genome(), fitness=0.5),
        ]
        # With k=3 (entire population), should always pick the fittest.
        winner = tournament_select(pop, k=3, rng=rng)
        assert winner.fitness == 0.9


class TestNextGeneration:
    def test_next_gen_preserves_population_size(self) -> None:
        rng = random.Random(42)
        pop = [Individual(genome=random_genome(rng), fitness=rng.random()) for _ in range(20)]
        next_gen = create_next_generation(
            pop,
            elite_count=3,
            sigma_frac=0.05,
            mutation_prob=0.2,
            rng=rng,
        )
        assert len(next_gen) == 20

    def test_elites_preserved(self) -> None:
        rng = random.Random(42)
        pop = [Individual(genome=random_genome(rng), fitness=float(i)) for i in range(10)]
        next_gen = create_next_generation(
            pop,
            elite_count=2,
            sigma_frac=0.05,
            mutation_prob=0.2,
            rng=rng,
        )
        # The top 2 genomes from the original should appear in next gen.
        top_genomes = {tuple(ind.genome) for ind in sorted(pop, key=lambda x: -x.fitness)[:2]}
        next_genomes = {tuple(ind.genome) for ind in next_gen}
        assert top_genomes.issubset(next_genomes)
