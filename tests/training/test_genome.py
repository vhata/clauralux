import json
import random
from pathlib import Path

from clauralux.training.genome import (
    NUM_PARAMS,
    PARAM_SPECS,
    clamp_genome,
    default_genome,
    dict_to_genome,
    genome_to_dict,
    load_genome,
    random_genome,
    save_genome,
)


class TestParamSpecs:
    def test_param_count(self) -> None:
        assert NUM_PARAMS == 25

    def test_unique_names(self) -> None:
        names = [p.name for p in PARAM_SPECS]
        assert len(names) == len(set(names))

    def test_defaults_within_range(self) -> None:
        for p in PARAM_SPECS:
            assert p.lo <= p.default <= p.hi, f"{p.name}: {p.default} not in [{p.lo}, {p.hi}]"

    def test_lo_less_than_hi(self) -> None:
        for p in PARAM_SPECS:
            assert p.lo < p.hi, f"{p.name}: lo={p.lo} >= hi={p.hi}"


class TestGenomeFunctions:
    def test_default_genome_length(self) -> None:
        g = default_genome()
        assert len(g) == NUM_PARAMS

    def test_random_genome_within_range(self) -> None:
        rng = random.Random(42)
        g = random_genome(rng)
        assert len(g) == NUM_PARAMS
        for p, v in zip(PARAM_SPECS, g, strict=True):
            assert p.lo <= v <= p.hi, f"{p.name}: {v} not in [{p.lo}, {p.hi}]"

    def test_clamp_genome(self) -> None:
        # Create a genome with out-of-range values.
        g = [p.hi + 10.0 for p in PARAM_SPECS]
        clamped = clamp_genome(g)
        for p, v in zip(PARAM_SPECS, clamped, strict=True):
            assert v == p.hi, f"{p.name}: expected {p.hi}, got {v}"

    def test_dict_roundtrip(self) -> None:
        g = default_genome()
        d = genome_to_dict(g)
        g2 = dict_to_genome(d)
        assert g == g2

    def test_dict_missing_keys_use_defaults(self) -> None:
        g = dict_to_genome({})
        assert g == default_genome()


class TestSerialization:
    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        g = default_genome()
        path = tmp_path / "weights.json"
        save_genome(g, path)
        g2 = load_genome(path)
        assert g == g2

    def test_save_produces_valid_json(self, tmp_path: Path) -> None:
        g = default_genome()
        path = tmp_path / "weights.json"
        save_genome(g, path)
        data = json.loads(path.read_text())
        assert isinstance(data, dict)
        assert len(data) == NUM_PARAMS
