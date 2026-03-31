"""Parameter definitions, ranges, and serialization for evolved bot genomes.

A genome is a flat list[float]. For the phase-based bot, the layout is:
  [early_params(25), mid_params(25), late_params(25), transition_1, transition_2]

Total: 77 values. This module defines what each parameter means, its valid
range, and how to save/load genomes as human-readable JSON.
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


# ── Per-Phase Parameter Space (25 parameters per phase) ─────────────────

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

NUM_PHASE_PARAMS: int = len(PARAM_SPECS)
NUM_PHASES: int = 3
PHASE_NAMES: tuple[str, ...] = ("early", "mid", "late")

# ── Phase Transition Parameters ─────────────────────────────────────────

TRANSITION_SPECS: tuple[ParamSpec, ...] = (
    ParamSpec("transition_1", 0.0, 3000.0, 500.0),
    ParamSpec("transition_2", 1000.0, 8000.0, 3000.0),
)

# Total genome size: 25 params * 3 phases + 2 transitions = 77.
NUM_PARAMS: int = NUM_PHASE_PARAMS * NUM_PHASES + len(TRANSITION_SPECS)

# Name→index lookup for fast access (per-phase params only).
_NAME_TO_INDEX: dict[str, int] = {p.name: i for i, p in enumerate(PARAM_SPECS)}

# All specs in genome order (phase0 params, phase1 params, phase2 params, transitions).
# Used by evolution operators that need per-gene ranges.
ALL_SPECS: tuple[ParamSpec, ...] = PARAM_SPECS * NUM_PHASES + TRANSITION_SPECS


# ── Genome construction ─────────────────────────────────────────────────


def default_genome() -> list[float]:
    """Return a genome initialised with all default values (3 identical phases)."""
    phase = [p.default for p in PARAM_SPECS]
    transitions = [t.default for t in TRANSITION_SPECS]
    return phase * NUM_PHASES + transitions


def random_genome(rng: random.Random | None = None) -> list[float]:
    """Return a genome with each parameter sampled uniformly within its range."""
    r = rng or random.Random()
    phases = [r.uniform(p.lo, p.hi) for _ in range(NUM_PHASES) for p in PARAM_SPECS]
    transitions = [r.uniform(t.lo, t.hi) for t in TRANSITION_SPECS]
    return phases + transitions


def clamp_genome(genome: list[float]) -> list[float]:
    """Clamp every parameter to its valid range."""
    result: list[float] = []
    for phase_idx in range(NUM_PHASES):
        offset = phase_idx * NUM_PHASE_PARAMS
        for i, spec in enumerate(PARAM_SPECS):
            result.append(max(spec.lo, min(spec.hi, genome[offset + i])))
    # Transition params.
    trans_offset = NUM_PHASE_PARAMS * NUM_PHASES
    for i, spec in enumerate(TRANSITION_SPECS):
        result.append(max(spec.lo, min(spec.hi, genome[trans_offset + i])))
    return result


# ── Conversion helpers ──────────────────────────────────────────────────


def genome_to_dict(genome: list[float]) -> dict[str, float]:
    """Convert a flat genome to a name-keyed dict (all 77 values).

    Keys are prefixed: early_w_garrison, mid_w_garrison, late_w_garrison,
    plus transition_1, transition_2.
    """
    d: dict[str, float] = {}
    for phase_idx in range(NUM_PHASES):
        prefix = PHASE_NAMES[phase_idx]
        offset = phase_idx * NUM_PHASE_PARAMS
        for i, spec in enumerate(PARAM_SPECS):
            d[f"{prefix}_{spec.name}"] = genome[offset + i]
    trans_offset = NUM_PHASE_PARAMS * NUM_PHASES
    for i, spec in enumerate(TRANSITION_SPECS):
        d[spec.name] = genome[trans_offset + i]
    return d


def dict_to_genome(d: dict[str, float]) -> list[float]:
    """Convert a name-keyed dict back to a flat genome.

    Missing keys get the default value.
    """
    result: list[float] = []
    for phase_idx in range(NUM_PHASES):
        prefix = PHASE_NAMES[phase_idx]
        for spec in PARAM_SPECS:
            result.append(d.get(f"{prefix}_{spec.name}", spec.default))
    for spec in TRANSITION_SPECS:
        result.append(d.get(spec.name, spec.default))
    return result


def genome_to_phase_dicts(
    genome: list[float],
) -> tuple[list[dict[str, float]], list[float]]:
    """Convert a flat genome to per-phase parameter dicts + transition values.

    Returns (phases, transitions) where phases is a list of 3 dicts
    and transitions is a list of 2 floats.
    """
    phases: list[dict[str, float]] = []
    for phase_idx in range(NUM_PHASES):
        offset = phase_idx * NUM_PHASE_PARAMS
        phase_dict = {spec.name: genome[offset + i] for i, spec in enumerate(PARAM_SPECS)}
        phases.append(phase_dict)
    trans_offset = NUM_PHASE_PARAMS * NUM_PHASES
    transitions = [genome[trans_offset + i] for i in range(len(TRANSITION_SPECS))]
    return phases, transitions


# ── Serialization ───────────────────────────────────────────────────────


def save_genome(genome: list[float], path: str | Path) -> None:
    """Save a genome to a JSON file in phase-based format."""
    phases, transitions = genome_to_phase_dicts(genome)
    data: dict[str, object] = {
        "phases": phases,
    }
    for i, spec in enumerate(TRANSITION_SPECS):
        data[spec.name] = transitions[i]
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def load_genome(path: str | Path) -> list[float]:
    """Load a genome from a JSON file.

    Supports both the new phase-based format (with "phases" key) and the
    old single-dict format (backwards compatible — loads as 3 identical phases).
    """
    raw = json.loads(Path(path).read_text())

    if "phases" in raw:
        # New format: {"phases": [...], "transition_1": ..., "transition_2": ...}
        genome: list[float] = []
        for phase_dict in raw["phases"]:
            for spec in PARAM_SPECS:
                genome.append(phase_dict.get(spec.name, spec.default))
        for spec in TRANSITION_SPECS:
            genome.append(raw.get(spec.name, spec.default))
        return genome
    else:
        # Old format: flat dict of 25 params — use as all 3 phases.
        phase_values = [raw.get(spec.name, spec.default) for spec in PARAM_SPECS]
        transitions = [spec.default for spec in TRANSITION_SPECS]
        return phase_values * NUM_PHASES + transitions


# ── Neural Network Genome ───────────────────────────────────────────────

NEURAL_NUM_FEATURES: int = 12
NEURAL_HIDDEN: int = 32
NEURAL_NUM_OUTPUTS: int = NUM_PHASE_PARAMS + 4  # 25 params + 4 priority weights

# Recurrent: previous hidden state feeds back as extra input.
NEURAL_INPUT_SIZE: int = NEURAL_NUM_FEATURES + NEURAL_HIDDEN  # 12 features + 32 hidden

# Weight layout: W_ih + b_h + W_ho + b_o
NEURAL_NUM_PARAMS: int = (
    NEURAL_INPUT_SIZE * NEURAL_HIDDEN  # input→hidden weights (features + prev hidden)
    + NEURAL_HIDDEN  # hidden biases
    + NEURAL_HIDDEN * NEURAL_NUM_OUTPUTS  # hidden→output weights
    + NEURAL_NUM_OUTPUTS  # output biases
)

# Range for neural network weights (used for mutation).
NEURAL_WEIGHT_RANGE = 3.0


def neural_random_genome(rng: random.Random | None = None) -> list[float]:
    """Xavier-initialized random genome for the neural network.

    Uses Xavier/Glorot initialization: weights ~ Uniform(-limit, limit)
    where limit = sqrt(6 / (fan_in + fan_out)).
    """
    import math

    r = rng or random.Random()
    genome: list[float] = []

    # Input→Hidden weights: Xavier with fan_in=44 (12 features + 32 hidden), fan_out=32.
    limit_ih = math.sqrt(6.0 / (NEURAL_INPUT_SIZE + NEURAL_HIDDEN))
    for _ in range(NEURAL_INPUT_SIZE * NEURAL_HIDDEN):
        genome.append(r.uniform(-limit_ih, limit_ih))

    # Hidden biases: zero-initialized.
    genome.extend([0.0] * NEURAL_HIDDEN)

    # Hidden→Output weights: Xavier with fan_in=32, fan_out=29.
    limit_ho = math.sqrt(6.0 / (NEURAL_HIDDEN + NEURAL_NUM_OUTPUTS))
    for _ in range(NEURAL_HIDDEN * NEURAL_NUM_OUTPUTS):
        genome.append(r.uniform(-limit_ho, limit_ho))

    # Output biases: zero-initialized.
    genome.extend([0.0] * NEURAL_NUM_OUTPUTS)

    return genome


def neural_save_genome(genome: list[float], path: str | Path) -> None:
    """Save a neural genome to a JSON file."""
    data = {"type": "neural", "weights": genome}
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def neural_load_genome(path: str | Path) -> list[float]:
    """Load a neural genome from a JSON file."""
    raw = json.loads(Path(path).read_text())
    if raw.get("type") == "neural":
        return raw["weights"]  # type: ignore[no-any-return]
    msg = f"Not a neural genome file: {path}"
    raise ValueError(msg)
