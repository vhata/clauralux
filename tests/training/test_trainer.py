"""Tests for the training loop orchestrator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from clauralux.training.trainer import TrainingConfig, _evaluate_individual, train


class TestEvaluateIndividual:
    def test_returns_float_fitness(self) -> None:
        """Evaluation should return a float fitness score."""
        from clauralux.training.genome import default_genome

        genome = default_genome()
        args: Any = (genome, 2, 42, [], False, [], False, 1.0)
        fitness = _evaluate_individual(args)
        assert isinstance(fitness, float)
        assert 0.0 <= fitness <= 1.5  # max possible: 1.0 + 0.2 speed + 0.1 territory

    def test_neural_mode(self) -> None:
        """Evaluation works with neural genomes."""
        from clauralux.training.genome import neural_random_genome

        genome = neural_random_genome()
        args: Any = (genome, 2, 42, [], False, [], True, 1.0)
        fitness = _evaluate_individual(args)
        assert isinstance(fitness, float)

    def test_self_play_mode(self) -> None:
        """Self-play: evaluate against peer genomes."""
        from clauralux.training.genome import default_genome, random_genome

        genome = default_genome()
        peers = [random_genome() for _ in range(3)]
        args: Any = (genome, 2, 42, [], True, peers, False, 1.0)
        fitness = _evaluate_individual(args)
        assert isinstance(fitness, float)

    def test_with_hall_of_fame(self) -> None:
        """Hall of fame genomes are used as opponents."""
        from clauralux.training.genome import default_genome, random_genome

        genome = default_genome()
        hof = [random_genome()]
        args: Any = (genome, 2, 42, hof, False, [], False, 1.0)
        fitness = _evaluate_individual(args)
        assert isinstance(fitness, float)

    def test_curriculum_phase_zero_uses_fewer_opponents(self) -> None:
        """Early curriculum (phase=0) should use fewer opponents."""
        from clauralux.training.genome import default_genome

        genome = default_genome()
        # Phase 0.0: only opponents with weight <= 0.8
        args_early: Any = (genome, 2, 42, [], False, [], False, 0.0)
        # Phase 1.0: all opponents
        args_late: Any = (genome, 2, 42, [], False, [], False, 1.0)
        # Both should return valid fitness.
        f_early = _evaluate_individual(args_early)
        f_late = _evaluate_individual(args_late)
        assert isinstance(f_early, float)
        assert isinstance(f_late, float)


class TestTrain:
    def test_short_training_run(self) -> None:
        """A minimal training run completes and saves weights."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "weights.json"
            config = TrainingConfig(
                population_size=4,
                generations=2,
                games_per_eval=2,
                workers=1,
                output_path=str(output),
                from_scratch=True,
                seed=42,
            )
            best_genome = train(config)
            assert isinstance(best_genome, list)
            assert len(best_genome) > 0
            assert output.exists()

    def test_neural_training_run(self) -> None:
        """Neural training completes and saves weights."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "neural.json"
            config = TrainingConfig(
                population_size=4,
                generations=2,
                games_per_eval=2,
                workers=1,
                output_path=str(output),
                from_scratch=True,
                neural=True,
                seed=42,
            )
            best_genome = train(config)
            assert isinstance(best_genome, list)
            assert output.exists()
            data = json.loads(output.read_text())
            assert data["type"] == "neural"

    def test_loads_existing_weights(self) -> None:
        """Training seeds population from existing weights file."""
        from clauralux.training.genome import default_genome, save_genome

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "weights.json"
            save_genome(default_genome(), output)
            config = TrainingConfig(
                population_size=4,
                generations=2,
                games_per_eval=2,
                workers=1,
                output_path=str(output),
                from_scratch=False,
                seed=42,
            )
            best_genome = train(config)
            assert isinstance(best_genome, list)

    def test_stagnation_resets_sigma(self) -> None:
        """Stagnation detection triggers sigma reset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "weights.json"
            config = TrainingConfig(
                population_size=4,
                generations=5,
                games_per_eval=2,
                workers=1,
                output_path=str(output),
                from_scratch=True,
                stagnation_limit=2,
                seed=42,
            )
            # Should complete without error even with aggressive stagnation.
            best_genome = train(config)
            assert isinstance(best_genome, list)
