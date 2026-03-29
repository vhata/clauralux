"""Parameter definitions, ranges, and serialization for evolved bot genomes.

A genome is a flat list[float] — one value per parameter. This module defines
what each parameter means, its valid range, and how to save/load genomes as
human-readable JSON.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Definition of a single genome parameter."""

    name: str
    lo: float
    hi: float
    default: float


# ── Parameter Space (26 parameters) ──────────────────────────────────────────

PARAM_SPECS: tuple[ParamSpec, ...] = (
    # Target scoring
    ParamSpec("w_garrison", 0.0, 5.0, 1.0),
    ParamSpec("w_distance", 0.0, 5.0, 0.5),
    ParamSpec("w_level", -2.0, 2.0, 0.3),
    ParamSpec("w_neutral_bonus", -2.0, 3.0, 1.0),
    ParamSpec("w_enemy_bonus", -2.0, 3.0, 0.0),
    ParamSpec("w_incoming_friendly", 0.0, 3.0, 0.5),
    # Force commitment
    ParamSpec("reserve_per_sun", 0.0, 15.0, 3.0),
    ParamSpec("min_force_ratio", 0.5, 5.0, 1.2),
    ParamSpec("send_fraction", 0.3, 1.0, 1.0),
    ParamSpec("concentrate_vs_split", 0.0, 1.0, 0.5),
    ParamSpec("max_targets_per_tick", 1.0, 5.0, 1.0),
    ParamSpec("overkill_aversion", 0.0, 2.0, 0.5),
    # Economy
    ParamSpec("upgrade_threshold", 10.0, 60.0, 25.0),
    ParamSpec("upgrade_vs_attack", 0.0, 1.0, 0.5),
    ParamSpec("max_upgrade_level", 1.0, 3.0, 3.0),
    ParamSpec("upgrade_when_no_targets", 0.0, 1.0, 0.7),
    ParamSpec("eco_phase_duration", 0.0, 2000.0, 500.0),
    # Timing
    ParamSpec("act_interval", 10.0, 40.0, 30.0),
    ParamSpec("early_aggression", 0.0, 1.0, 0.3),
    ParamSpec("patience", 0.0, 2.0, 1.0),
    # Multi-sun coordination
    ParamSpec("nearest_sun_weight", 0.0, 3.0, 1.0),
    ParamSpec("reinforce_own", 0.0, 1.0, 0.2),
    ParamSpec("defensive_garrison_threshold", 0.0, 30.0, 5.0),
    # Threat assessment
    ParamSpec("w_enemy_incoming", 0.0, 3.0, 1.0),
    ParamSpec("threat_response", 0.0, 1.0, 0.5),
)

NUM_PARAMS: int = len(PARAM_SPECS)

# Name→index lookup for fast access.
_NAME_TO_INDEX: dict[str, int] = {p.name: i for i, p in enumerate(PARAM_SPECS)}


def default_genome() -> list[float]:
    """Return a genome initialised with all default values."""
    return [p.default for p in PARAM_SPECS]


def random_genome(rng: random.Random | None = None) -> list[float]:
    """Return a genome with each parameter sampled uniformly within its range."""
    r = rng or random.Random()
    return [r.uniform(p.lo, p.hi) for p in PARAM_SPECS]


def clamp_genome(genome: list[float]) -> list[float]:
    """Clamp every parameter to its valid range."""
    return [max(p.lo, min(p.hi, v)) for p, v in zip(PARAM_SPECS, genome, strict=True)]


def genome_to_dict(genome: list[float]) -> dict[str, float]:
    """Convert a genome list to a name-keyed dict (for readability/serialization)."""
    return {p.name: v for p, v in zip(PARAM_SPECS, genome, strict=True)}


def dict_to_genome(d: dict[str, float]) -> list[float]:
    """Convert a name-keyed dict back to a genome list.

    Missing keys get the default value.
    """
    return [d.get(p.name, p.default) for p in PARAM_SPECS]


def save_genome(genome: list[float], path: str | Path) -> None:
    """Save a genome to a JSON file (keyed by parameter name)."""
    data = genome_to_dict(genome)
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def load_genome(path: str | Path) -> list[float]:
    """Load a genome from a JSON file."""
    data = json.loads(Path(path).read_text())
    return dict_to_genome(data)
