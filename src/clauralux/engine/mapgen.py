from __future__ import annotations

import dataclasses
import random
from dataclasses import dataclass
from typing import Any

from .config import GameConfig
from .state import GameState, Sun
from .types import NEUTRAL, PlayerId, Position, SunId

FLAVOURS: dict[str, FlavourParams] = {}


@dataclass(frozen=True, slots=True)
class FlavourParams:
    """Parameters that define a map generation flavour."""

    total_suns: tuple[int, int]  # (min, max) including player suns
    neutral_garrison: tuple[float, float]  # (min, max) for neutral garrisons
    min_sun_spacing: float  # minimum distance between any two suns
    player_edge_bias: float  # 0.0=centre, 1.0=edges
    config_overrides: dict[str, Any]


FLAVOURS = {
    "strategic": FlavourParams(
        total_suns=(12, 16),
        neutral_garrison=(15.0, 30.0),
        min_sun_spacing=120.0,
        player_edge_bias=0.9,
        config_overrides={
            "production_interval": 50,
            "unit_speed": 1.5,
        },
    ),
    "rush": FlavourParams(
        total_suns=(4, 6),
        neutral_garrison=(3.0, 8.0),
        min_sun_spacing=60.0,
        player_edge_bias=0.5,
        config_overrides={
            "production_interval": 15,
            "unit_speed": 3.0,
        },
    ),
    "chokepoint": FlavourParams(
        total_suns=(8, 10),
        neutral_garrison=(20.0, 40.0),
        min_sun_spacing=80.0,
        player_edge_bias=1.0,
        config_overrides={
            "attack_ratio": 0.8,
        },
    ),
    "swarm": FlavourParams(
        total_suns=(14, 20),
        neutral_garrison=(5.0, 10.0),
        min_sun_spacing=50.0,
        player_edge_bias=0.7,
        config_overrides={
            "production_interval": 15,
            "upgrade_costs": (10, 20),
        },
    ),
}


def flavour_config(base: GameConfig, flavour: str) -> GameConfig:
    """Return a new GameConfig with flavour-specific overrides applied."""
    params = FLAVOURS.get(flavour)
    if params is None:
        return base
    return dataclasses.replace(base, **params.config_overrides)


def generate_map(
    config: GameConfig,
    flavour: str,
    num_players: int,
    seed: int | None = None,
) -> GameState:
    """Generate a random map matching the given flavour."""
    params = FLAVOURS[flavour]
    rng = random.Random(seed)

    margin = 50.0
    w, h = config.map_width, config.map_height

    # Place player suns on edges/periphery.
    player_positions = _place_players(w, h, num_players, params.player_edge_bias, margin)

    # Determine total sun count.
    total = rng.randint(*params.total_suns)
    total = max(total, num_players)  # at least one per player
    num_neutrals = total - num_players

    # Build placed list starting with player suns.
    placed: list[Position] = list(player_positions)

    # Place neutrals via rejection sampling.
    if flavour == "chokepoint":
        neutrals = _place_chokepoint_neutrals(
            w, h, num_neutrals, params.min_sun_spacing, placed, margin, rng
        )
    else:
        neutrals = _place_random_neutrals(
            w, h, num_neutrals, params.min_sun_spacing, placed, margin, rng
        )
    placed.extend(neutrals)

    # Build game state.
    suns: dict[SunId, Sun] = {}
    sun_id = 0

    for i, pos in enumerate(player_positions):
        pid = PlayerId(i + 1)
        suns[SunId(sun_id)] = Sun(
            id=SunId(sun_id),
            position=pos,
            owner=pid,
            garrison=config.default_player_garrison,
        )
        sun_id += 1

    for pos in neutrals:
        garrison = rng.uniform(*params.neutral_garrison)
        suns[SunId(sun_id)] = Sun(
            id=SunId(sun_id),
            position=pos,
            owner=NEUTRAL,
            garrison=garrison,
        )
        sun_id += 1

    players = [PlayerId(i + 1) for i in range(num_players)]
    return GameState(suns=suns, players=players)


def _place_players(
    w: float,
    h: float,
    num_players: int,
    edge_bias: float,
    margin: float,
) -> list[Position]:
    """Place players around the map edges."""
    cx, cy = w / 2, h / 2
    rx = (w / 2 - margin) * edge_bias
    ry = (h / 2 - margin) * edge_bias

    positions: list[Position] = []
    for i in range(num_players):
        angle = (2 * 3.14159265 * i / num_players) - 3.14159265 / 2
        x = cx + rx * _cos(angle)
        y = cy + ry * _sin(angle)
        positions.append(Position(x, y))
    return positions


def _place_random_neutrals(
    w: float,
    h: float,
    count: int,
    min_spacing: float,
    placed: list[Position],
    margin: float,
    rng: random.Random,
) -> list[Position]:
    """Place neutrals via rejection sampling with minimum spacing."""
    neutrals: list[Position] = []
    all_positions = list(placed)

    for _ in range(count):
        for _attempt in range(200):
            x = rng.uniform(margin, w - margin)
            y = rng.uniform(margin, h - margin)
            pos = Position(x, y)
            if all(pos.distance_to(p) >= min_spacing for p in all_positions):
                neutrals.append(pos)
                all_positions.append(pos)
                break

    return neutrals


def _place_chokepoint_neutrals(
    w: float,
    h: float,
    count: int,
    min_spacing: float,
    placed: list[Position],
    margin: float,
    rng: random.Random,
) -> list[Position]:
    """Place neutrals along 2-3 horizontal lanes to create chokepoints."""
    num_lanes = rng.choice([2, 3])
    lane_ys = [h * (i + 1) / (num_lanes + 1) for i in range(num_lanes)]

    neutrals: list[Position] = []
    all_positions = list(placed)
    lane_spread = h * 0.08  # how far off the lane centre a sun can be

    for _ in range(count):
        for _attempt in range(200):
            lane_y = rng.choice(lane_ys)
            x = rng.uniform(margin, w - margin)
            y = lane_y + rng.uniform(-lane_spread, lane_spread)
            y = max(margin, min(h - margin, y))
            pos = Position(x, y)
            if all(pos.distance_to(p) >= min_spacing for p in all_positions):
                neutrals.append(pos)
                all_positions.append(pos)
                break

    return neutrals


def _cos(angle: float) -> float:
    import math

    return math.cos(angle)


def _sin(angle: float) -> float:
    import math

    return math.sin(angle)
