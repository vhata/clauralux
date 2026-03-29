from __future__ import annotations

from .config import GameConfig
from .state import GameState, Sun
from .types import NEUTRAL, PlayerId, Position, SunId


def two_player_simple(config: GameConfig) -> GameState:
    """A simple symmetric 2-player map: 2 player suns + 3 neutrals."""
    p1 = PlayerId(1)
    p2 = PlayerId(2)
    w, h = config.map_width, config.map_height

    suns = {
        SunId(0): Sun(
            id=SunId(0),
            position=Position(w * 0.15, h * 0.5),
            owner=p1,
            garrison=config.default_player_garrison,
        ),
        SunId(1): Sun(
            id=SunId(1),
            position=Position(w * 0.85, h * 0.5),
            owner=p2,
            garrison=config.default_player_garrison,
        ),
        SunId(2): Sun(
            id=SunId(2),
            position=Position(w * 0.5, h * 0.2),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
        SunId(3): Sun(
            id=SunId(3),
            position=Position(w * 0.5, h * 0.5),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
        SunId(4): Sun(
            id=SunId(4),
            position=Position(w * 0.5, h * 0.8),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
    }

    return GameState(suns=suns, players=[p1, p2])


def three_player_triangle(config: GameConfig) -> GameState:
    """A 3-player map with players at triangle vertices and neutrals between."""
    p1 = PlayerId(1)
    p2 = PlayerId(2)
    p3 = PlayerId(3)
    w, h = config.map_width, config.map_height

    suns = {
        SunId(0): Sun(
            id=SunId(0),
            position=Position(w * 0.5, h * 0.1),
            owner=p1,
            garrison=config.default_player_garrison,
        ),
        SunId(1): Sun(
            id=SunId(1),
            position=Position(w * 0.15, h * 0.85),
            owner=p2,
            garrison=config.default_player_garrison,
        ),
        SunId(2): Sun(
            id=SunId(2),
            position=Position(w * 0.85, h * 0.85),
            owner=p3,
            garrison=config.default_player_garrison,
        ),
        # Neutrals between each pair
        SunId(3): Sun(
            id=SunId(3),
            position=Position(w * 0.325, h * 0.475),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
        SunId(4): Sun(
            id=SunId(4),
            position=Position(w * 0.675, h * 0.475),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
        SunId(5): Sun(
            id=SunId(5),
            position=Position(w * 0.5, h * 0.85),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
        # Center
        SunId(6): Sun(
            id=SunId(6),
            position=Position(w * 0.5, h * 0.5),
            owner=NEUTRAL,
            garrison=config.default_neutral_garrison,
        ),
    }

    return GameState(suns=suns, players=[p1, p2, p3])
