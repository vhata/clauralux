import json
import random
from pathlib import Path

from clauralux.training.genome import (
    ALL_SPECS,
    NUM_PARAMS,
    NUM_PHASE_PARAMS,
    NUM_PHASES,
    PARAM_SPECS,
    TRANSITION_SPECS,
    clamp_genome,
    default_genome,
    dict_to_genome,
    genome_to_dict,
    genome_to_phase_dicts,
    load_genome,
    random_genome,
    save_genome,
)


class TestParamSpecs:
    def test_param_count(self) -> None:
        assert NUM_PHASE_PARAMS == 25
        assert NUM_PARAMS == 77  # 25 * 3 + 2

    def test_all_specs_length(self) -> None:
        assert len(ALL_SPECS) == NUM_PARAMS

    def test_unique_names(self) -> None:
        names = [p.name for p in PARAM_SPECS]
        assert len(names) == len(set(names))

    def test_defaults_within_range(self) -> None:
        for p in PARAM_SPECS:
            assert p.lo <= p.default <= p.hi, f"{p.name}: {p.default} not in [{p.lo}, {p.hi}]"
        for p in TRANSITION_SPECS:
            assert p.lo <= p.default <= p.hi, f"{p.name}: {p.default} not in [{p.lo}, {p.hi}]"

    def test_lo_less_than_hi(self) -> None:
        for p in (*PARAM_SPECS, *TRANSITION_SPECS):
            assert p.lo < p.hi, f"{p.name}: lo={p.lo} >= hi={p.hi}"


class TestGenomeFunctions:
    def test_default_genome_length(self) -> None:
        g = default_genome()
        assert len(g) == NUM_PARAMS

    def test_random_genome_length_and_range(self) -> None:
        rng = random.Random(42)
        g = random_genome(rng)
        assert len(g) == NUM_PARAMS
        for spec, v in zip(ALL_SPECS, g, strict=True):
            assert spec.lo <= v <= spec.hi, f"{spec.name}: {v} not in [{spec.lo}, {spec.hi}]"

    def test_clamp_genome(self) -> None:
        g = [spec.hi + 10.0 for spec in ALL_SPECS]
        clamped = clamp_genome(g)
        for spec, v in zip(ALL_SPECS, clamped, strict=True):
            assert v == spec.hi, f"{spec.name}: expected {spec.hi}, got {v}"

    def test_dict_roundtrip(self) -> None:
        g = default_genome()
        d = genome_to_dict(g)
        g2 = dict_to_genome(d)
        assert g == g2

    def test_dict_missing_keys_use_defaults(self) -> None:
        g = dict_to_genome({})
        assert g == default_genome()

    def test_phase_dicts(self) -> None:
        g = default_genome()
        phases, transitions = genome_to_phase_dicts(g)
        assert len(phases) == NUM_PHASES
        assert len(transitions) == len(TRANSITION_SPECS)
        # All phases should be identical for default genome.
        assert phases[0] == phases[1] == phases[2]
        assert len(phases[0]) == NUM_PHASE_PARAMS

    def test_phase_dicts_different_phases(self) -> None:
        rng = random.Random(42)
        g = random_genome(rng)
        phases, _ = genome_to_phase_dicts(g)
        # Random genome should have different phase values.
        assert phases[0] != phases[1]


class TestSerialization:
    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        g = default_genome()
        path = tmp_path / "weights.json"
        save_genome(g, path)
        g2 = load_genome(path)
        assert g == g2

    def test_save_produces_phase_format(self, tmp_path: Path) -> None:
        g = default_genome()
        path = tmp_path / "weights.json"
        save_genome(g, path)
        data = json.loads(path.read_text())
        assert "phases" in data
        assert len(data["phases"]) == NUM_PHASES
        assert "transition_1" in data
        assert "transition_2" in data

    def test_load_old_format_backwards_compat(self, tmp_path: Path) -> None:
        """Old single-dict format should load as 3 identical phases."""
        old_data = {spec.name: spec.default for spec in PARAM_SPECS}
        path = tmp_path / "old_weights.json"
        path.write_text(json.dumps(old_data))
        g = load_genome(path)
        assert len(g) == NUM_PARAMS
        phases, transitions = genome_to_phase_dicts(g)
        assert phases[0] == phases[1] == phases[2]
        # Transitions should be defaults.
        for i, spec in enumerate(TRANSITION_SPECS):
            assert transitions[i] == spec.default
