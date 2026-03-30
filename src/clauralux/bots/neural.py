"""Neural network bot — an MLP reads game state and outputs decision parameters.

The network takes 12 game-state features as input and produces 29 outputs:
25 heuristic parameters (same as EvolvedBot) + 4 priority weights that
control the order of defend/reinforce/upgrade/attack decisions.

All decision logic (target scoring, dispatch, threats, upgrades) is inherited
from EvolvedBot. The neural net just decides *how* to tune that logic each tick.
"""

from __future__ import annotations

import math
from pathlib import Path

from clauralux.engine.actions import Action
from clauralux.engine.view import GameView
from clauralux.training.genome import (
    NEURAL_HIDDEN,
    NEURAL_NUM_FEATURES,
    NEURAL_NUM_OUTPUTS,
    NEURAL_NUM_PARAMS,
    PARAM_SPECS,
    neural_load_genome,
    neural_random_genome,
)

from .evolved import EvolvedBot

DEFAULT_NEURAL_WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "data" / "neural_weights.json"

# Action handler names in the order EvolvedBot uses them.
_ACTION_NAMES = ("threats", "reinforce", "upgrade", "attack")


# ── Feature Extraction ──────────────────────────────────────────────────


def extract_features(view: GameView) -> list[float]:
    """Extract 12 normalized features from the current game state."""
    max_ticks = view.config.max_ticks or 10_000
    max_level = view.config.max_sun_level
    total_suns = max(len(view.suns), 1)

    my_suns = view.my_suns()
    enemy_suns = view.enemy_suns()
    neutral_suns = view.neutral_suns()

    my_garrison = sum(s.garrison for s in my_suns)
    enemy_garrison = sum(s.garrison for s in enemy_suns)
    total_garrison = max(my_garrison + enemy_garrison, 1.0)

    my_flight = sum(g.count for g in view.my_unit_groups())
    enemy_flight = sum(g.count for g in view.enemy_unit_groups())
    total_flight = max(my_flight + enemy_flight, 1.0)

    my_level_sum = sum(s.level for s in my_suns) if my_suns else 0.0
    enemy_level_sum = sum(s.level for s in enemy_suns) if enemy_suns else 0.0
    total_level = max(my_level_sum + enemy_level_sum, 1.0)

    my_avg_level = (my_level_sum / max(len(my_suns), 1)) / max(max_level, 1)
    enemy_avg_level = (enemy_level_sum / max(len(enemy_suns), 1)) / max(max_level, 1)

    # Production rate approximation: sum of levels for owned suns.
    total_production = max(my_level_sum + enemy_level_sum, 1.0)

    # Threat: enemy units heading at my suns.
    my_sun_ids = {s.id for s in my_suns}
    enemy_incoming = sum(g.count for g in view.enemy_unit_groups() if g.target_sun_id in my_sun_ids)
    threat = enemy_incoming / max(my_garrison, 1.0)

    my_sun_count = len(my_suns)
    enemy_sun_count = len(enemy_suns)
    contested_suns = max(my_sun_count + enemy_sun_count, 1)

    return [
        min(1.0, view.tick / max_ticks),  # tick_fraction
        my_sun_count / total_suns,  # my_sun_ratio
        enemy_sun_count / total_suns,  # enemy_sun_ratio
        len(neutral_suns) / total_suns,  # neutral_sun_ratio
        my_garrison / total_garrison,  # garrison_ratio
        my_flight / total_flight,  # flight_ratio
        min(1.0, my_avg_level),  # my_avg_level
        min(1.0, enemy_avg_level),  # enemy_avg_level
        my_level_sum / total_production,  # production_ratio
        min(1.0, threat),  # threat_level
        my_sun_count / contested_suns,  # territory_control
        my_level_sum / total_level,  # eco_advantage
    ]


# ── MLP Forward Pass ────────────────────────────────────────────────────


def _sigmoid(x: float) -> float:
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    return math.tanh(x)


def mlp_forward(
    features: list[float],
    weights: list[float],
    num_features: int = NEURAL_NUM_FEATURES,
    num_hidden: int = NEURAL_HIDDEN,
    num_outputs: int = NEURAL_NUM_OUTPUTS,
) -> list[float]:
    """Pure-Python MLP forward pass: input → hidden (tanh) → output (sigmoid).

    Weight layout in the flat list:
      [W_ih (features*hidden), b_h (hidden), W_ho (hidden*outputs), b_o (outputs)]
    """
    idx = 0

    # Input → Hidden.
    w_ih_size = num_features * num_hidden
    hidden = [0.0] * num_hidden
    for h in range(num_hidden):
        total = 0.0
        for f in range(num_features):
            total += features[f] * weights[idx + h * num_features + f]
        hidden[h] = total
    idx += w_ih_size

    # Hidden bias.
    for h in range(num_hidden):
        hidden[h] = _tanh(hidden[h] + weights[idx + h])
    idx += num_hidden

    # Hidden → Output.
    w_ho_size = num_hidden * num_outputs
    output = [0.0] * num_outputs
    for o in range(num_outputs):
        total = 0.0
        for h in range(num_hidden):
            total += hidden[h] * weights[idx + o * num_hidden + h]
        output[o] = total
    idx += w_ho_size

    # Output bias + sigmoid activation.
    for o in range(num_outputs):
        output[o] = _sigmoid(output[o] + weights[idx + o])

    return output


def decode_outputs(
    raw_outputs: list[float],
) -> tuple[dict[str, float], list[int]]:
    """Decode MLP outputs into parameter dict + priority ordering.

    First 25 outputs → scaled to each ParamSpec's [lo, hi] range.
    Last 4 outputs → sorted descending to give action priority order.
    """
    params: dict[str, float] = {}
    for i, spec in enumerate(PARAM_SPECS):
        # raw_outputs[i] is sigmoid (0-1), scale to [lo, hi].
        params[spec.name] = spec.lo + raw_outputs[i] * (spec.hi - spec.lo)

    # Priority weights: indices 25-28.
    priority_raw = raw_outputs[len(PARAM_SPECS) : len(PARAM_SPECS) + 4]
    # Sort by weight descending → gives action execution order.
    priority_order = sorted(range(4), key=lambda i: -priority_raw[i])

    return params, priority_order


# ── NeuralBot ───────────────────────────────────────────────────────────


class NeuralBot(EvolvedBot):
    """Neural network bot — MLP outputs heuristic parameters each tick."""

    def __init__(
        self,
        genome: list[float] | None = None,
        weights_path: str | Path | None = None,
    ) -> None:
        # Skip EvolvedBot.__init__ — we handle genome differently.
        # Call Bot.__init__ directly.
        from .base import Bot

        Bot.__init__(self)

        if genome is not None:
            self._weights = genome
        elif weights_path is not None:
            self._weights = neural_load_genome(weights_path)
        else:
            try:
                self._weights = neural_load_genome(DEFAULT_NEURAL_WEIGHTS_PATH)
            except FileNotFoundError:
                self._weights = neural_random_genome()

        assert len(self._weights) == NEURAL_NUM_PARAMS, (
            f"Expected {NEURAL_NUM_PARAMS} weights, got {len(self._weights)}"
        )

        # Initialize _p and phase data so inherited methods work.
        self._p: dict[str, float] = {spec.name: spec.default for spec in PARAM_SPECS}
        self._phases = [dict(self._p)]
        self._transitions = [500.0, 3000.0]

    def decide(self, view: GameView) -> list[Action]:
        # Extract features and run forward pass.
        features = extract_features(view)
        raw = mlp_forward(features, self._weights)
        params, priority = decode_outputs(raw)

        # Set active parameters.
        self._p = params

        act_interval = max(1, int(params["act_interval"]))
        if view.tick % act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "[neural] No suns. Waiting for the end."
            return []

        reserve = params["reserve_per_sun"]
        available_per_sun = {s.id: max(0.0, s.garrison - reserve) for s in my_suns}
        total_available = sum(available_per_sun.values())

        if total_available <= 0:
            self._intent = "[neural] Building up garrison reserves."
            return []

        # Execute action handlers in neural-determined priority order.
        handlers = [
            lambda: self._handle_threats(view, my_suns, available_per_sun),
            lambda: self._handle_reinforce(view, my_suns, available_per_sun),
            lambda: self._handle_upgrade(view, my_suns, total_available),
            lambda: self._handle_attack(view, my_suns, available_per_sun, total_available),
        ]

        for action_idx in priority:
            actions = handlers[action_idx]()
            if actions:
                return actions

        self._intent = "[neural] No actions taken."
        return []
