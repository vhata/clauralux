"""Neural network bot — a recurrent MLP reads game state and outputs decision parameters.

The network takes 12 game-state features + 32 recurrent hidden-state values as
input and produces 29 outputs: 25 heuristic parameters (same as EvolvedBot) +
4 priority weights that control the order of defend/reinforce/upgrade/attack
decisions. The hidden state carries forward between ticks, giving the network
memory of past game states.

All decision logic (target scoring, dispatch, threats, upgrades) is inherited
from EvolvedBot. The neural net just decides *how* to tune that logic each tick.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from clauralux.engine.actions import Action
from clauralux.engine.view import GameView, SunView
from clauralux.training.genome import (
    NEURAL_HIDDEN,
    NEURAL_INPUT_SIZE,
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
    """Extract 20 normalized features from the current game state.

    Features 0-11: original aggregate features (ratios, levels, threats).
    Features 12-19: spatial and distribution features for map awareness.
    """
    max_ticks = view.config.max_ticks or 10_000
    max_level = view.config.max_sun_level
    total_suns = max(len(view.suns), 1)
    map_diag = (view.config.map_width**2 + view.config.map_height**2) ** 0.5

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

    # ── Spatial features ───────────────────────────────────────────────

    # Nearest distance from any of my suns to an enemy sun (normalized).
    min_dist_to_enemy = 1.0
    if my_suns and enemy_suns:
        min_dist_to_enemy = min(_sun_dist(ms, es) / map_diag for ms in my_suns for es in enemy_suns)

    # Nearest distance from any of my suns to a neutral sun.
    min_dist_to_neutral = 1.0
    if my_suns and neutral_suns:
        min_dist_to_neutral = min(
            _sun_dist(ms, ns) / map_diag for ms in my_suns for ns in neutral_suns
        )

    # Weakest enemy garrison (normalized by total garrison).
    weakest_enemy_garrison = 0.0
    if enemy_suns:
        weakest_enemy_garrison = min(s.garrison for s in enemy_suns) / max(total_garrison, 1.0)

    # Strongest own garrison (normalized).
    strongest_own_garrison = 0.0
    if my_suns:
        strongest_own_garrison = max(s.garrison for s in my_suns) / max(total_garrison, 1.0)

    # Garrison concentration: std_dev / mean of own garrisons (0 = even, high = concentrated).
    garrison_concentration = 0.0
    if len(my_suns) > 1:
        my_garrs = [float(s.garrison) for s in my_suns]
        mean_g = sum(my_garrs) / len(my_garrs)
        if mean_g > 0:
            variance = sum((g - mean_g) ** 2 for g in my_garrs) / len(my_garrs)
            garrison_concentration = min(1.0, (variance**0.5) / mean_g)

    # Number of enemy groups heading at my suns (engagement pressure).
    enemy_wave_count = sum(1 for g in view.enemy_unit_groups() if g.target_sun_id in my_sun_ids)
    wave_pressure = min(1.0, enemy_wave_count / max(my_sun_count, 1))

    # Friendly units heading to enemy suns (offensive commitment).
    enemy_sun_ids = {s.id for s in enemy_suns}
    my_offensive = sum(g.count for g in view.my_unit_groups() if g.target_sun_id in enemy_sun_ids)
    offensive_commitment = my_offensive / max(my_garrison + my_flight, 1.0)

    # Number of players still alive (multi-player awareness).
    alive = len(view.players) - len(view.eliminated)
    multi_player = min(1.0, (alive - 1) / max(len(view.players) - 1, 1))

    return [
        # Original 12 features.
        min(1.0, view.tick / max_ticks),  # 0: tick_fraction
        my_sun_count / total_suns,  # 1: my_sun_ratio
        enemy_sun_count / total_suns,  # 2: enemy_sun_ratio
        len(neutral_suns) / total_suns,  # 3: neutral_sun_ratio
        my_garrison / total_garrison,  # 4: garrison_ratio
        my_flight / total_flight,  # 5: flight_ratio
        min(1.0, my_avg_level),  # 6: my_avg_level
        min(1.0, enemy_avg_level),  # 7: enemy_avg_level
        my_level_sum / total_production,  # 8: production_ratio
        min(1.0, threat),  # 9: threat_level
        my_sun_count / contested_suns,  # 10: territory_control
        my_level_sum / total_level,  # 11: eco_advantage
        # New spatial/distribution features.
        min_dist_to_enemy,  # 12: nearest enemy distance
        min_dist_to_neutral,  # 13: nearest neutral distance
        weakest_enemy_garrison,  # 14: weakest enemy garrison
        strongest_own_garrison,  # 15: strongest own garrison
        garrison_concentration,  # 16: garrison spread
        wave_pressure,  # 17: incoming attack pressure
        offensive_commitment,  # 18: units committed to attacks
        multi_player,  # 19: alive player ratio
    ]


def _sun_dist(a: SunView, b: SunView) -> float:
    dx = float(a.position.x - b.position.x)
    dy = float(a.position.y - b.position.y)
    return float((dx * dx + dy * dy) ** 0.5)


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
    prev_hidden: np.ndarray | None = None,
    num_input: int = NEURAL_INPUT_SIZE,
    num_hidden: int = NEURAL_HIDDEN,
    num_outputs: int = NEURAL_NUM_OUTPUTS,
) -> tuple[list[float], np.ndarray]:
    """NumPy-accelerated recurrent MLP forward pass.

    Input is features concatenated with previous hidden state.
    Returns (outputs, new_hidden_state).

    Weight layout in the flat list:
      [W_ih (input*hidden), b_h (hidden), W_ho (hidden*outputs), b_o (outputs)]
    """
    w = np.array(weights)
    x_features = np.array(features)

    if prev_hidden is None:
        prev_hidden = np.zeros(num_hidden)

    # Concatenate features with previous hidden state.
    x = np.concatenate([x_features, prev_hidden])

    idx = 0

    # Input → Hidden: W_ih is (num_hidden, num_input), stored row-major.
    w_ih = w[idx : idx + num_input * num_hidden].reshape(num_hidden, num_input)
    idx += num_input * num_hidden

    b_h = w[idx : idx + num_hidden]
    idx += num_hidden

    hidden = np.tanh(w_ih @ x + b_h)

    # Hidden → Output: W_ho is (num_outputs, num_hidden), stored row-major.
    w_ho = w[idx : idx + num_hidden * num_outputs].reshape(num_outputs, num_hidden)
    idx += num_hidden * num_outputs

    b_o = w[idx : idx + num_outputs]

    # Sigmoid activation with clipping for numerical stability.
    z = w_ho @ hidden + b_o
    z = np.clip(z, -500.0, 500.0)
    output = 1.0 / (1.0 + np.exp(-z))

    result: list[float] = output.tolist()
    return result, hidden


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

        # Recurrent hidden state — carried forward between ticks.
        self._hidden: np.ndarray | None = None

    def on_game_start(self, view: GameView) -> None:
        self._hidden = None

    def decide(self, view: GameView) -> list[Action]:
        # Extract features and run forward pass with recurrent state.
        features = extract_features(view)
        raw, self._hidden = mlp_forward(features, self._weights, self._hidden)
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
