from __future__ import annotations

import math

from .config import GameConfig
from .state import GameState, Sun
from .types import NEUTRAL, PlayerId, Position, SunId


def _sun(sun_id: int, x: float, y: float, owner: PlayerId, garrison: float) -> tuple[SunId, Sun]:
    sid = SunId(sun_id)
    return sid, Sun(id=sid, position=Position(x, y), owner=owner, garrison=garrison)


def two_player_simple(config: GameConfig) -> GameState:
    """A simple symmetric 2-player map: 2 player suns + 3 neutrals."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, p1, g),
            _sun(1, w * 0.85, h * 0.5, p2, g),
            _sun(2, w * 0.5, h * 0.2, NEUTRAL, ng),
            _sun(3, w * 0.5, h * 0.5, NEUTRAL, ng),
            _sun(4, w * 0.5, h * 0.8, NEUTRAL, ng),
        ]
    )
    return GameState(suns=suns, players=[p1, p2])


def three_player_triangle(config: GameConfig) -> GameState:
    """3 players at triangle vertices with neutrals between."""
    p1, p2, p3 = PlayerId(1), PlayerId(2), PlayerId(3)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.1, p1, g),
            _sun(1, w * 0.15, h * 0.85, p2, g),
            _sun(2, w * 0.85, h * 0.85, p3, g),
            _sun(3, w * 0.325, h * 0.475, NEUTRAL, ng),
            _sun(4, w * 0.675, h * 0.475, NEUTRAL, ng),
            _sun(5, w * 0.5, h * 0.85, NEUTRAL, ng),
            _sun(6, w * 0.5, h * 0.5, NEUTRAL, ng),
        ]
    )
    return GameState(suns=suns, players=[p1, p2, p3])


def four_player_cross(config: GameConfig) -> GameState:
    """4 players at compass points with neutrals in between."""
    players = [PlayerId(i + 1) for i in range(4)]
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.08, players[0], g),  # north
            _sun(1, w * 0.92, h * 0.5, players[1], g),  # east
            _sun(2, w * 0.5, h * 0.92, players[2], g),  # south
            _sun(3, w * 0.08, h * 0.5, players[3], g),  # west
            # Neutrals between each adjacent pair
            _sun(4, w * 0.72, h * 0.28, NEUTRAL, ng),
            _sun(5, w * 0.72, h * 0.72, NEUTRAL, ng),
            _sun(6, w * 0.28, h * 0.72, NEUTRAL, ng),
            _sun(7, w * 0.28, h * 0.28, NEUTRAL, ng),
            # Centre
            _sun(8, w * 0.5, h * 0.5, NEUTRAL, ng * 1.5),
        ]
    )
    return GameState(suns=suns, players=players)


def five_player_pentagon(config: GameConfig) -> GameState:
    """5 players arranged in a pentagon with neutrals."""
    players = [PlayerId(i + 1) for i in range(5)]
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison
    cx, cy = w * 0.5, h * 0.5
    r = min(w, h) * 0.4

    suns_list: list[tuple[SunId, Sun]] = []
    sid = 0

    # Player suns on pentagon vertices.
    for i, pid in enumerate(players):
        angle = (2 * math.pi * i / 5) - math.pi / 2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        suns_list.append(_sun(sid, x, y, pid, g))
        sid += 1

    # Neutrals between each adjacent pair.
    for i in range(5):
        j = (i + 1) % 5
        ax = cx + r * math.cos((2 * math.pi * i / 5) - math.pi / 2)
        ay = cy + r * math.sin((2 * math.pi * i / 5) - math.pi / 2)
        bx = cx + r * math.cos((2 * math.pi * j / 5) - math.pi / 2)
        by = cy + r * math.sin((2 * math.pi * j / 5) - math.pi / 2)
        suns_list.append(_sun(sid, (ax + bx) / 2, (ay + by) / 2, NEUTRAL, ng))
        sid += 1

    # Centre.
    suns_list.append(_sun(sid, cx, cy, NEUTRAL, ng * 1.5))

    return GameState(suns=dict(suns_list), players=players)


def six_player_hex(config: GameConfig) -> GameState:
    """6 players in a hexagonal arrangement with neutrals."""
    players = [PlayerId(i + 1) for i in range(6)]
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison
    cx, cy = w * 0.5, h * 0.5
    r = min(w, h) * 0.4

    suns_list: list[tuple[SunId, Sun]] = []
    sid = 0

    # Player suns on hexagon vertices.
    for i, pid in enumerate(players):
        angle = (2 * math.pi * i / 6) - math.pi / 2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        suns_list.append(_sun(sid, x, y, pid, g))
        sid += 1

    # Neutrals between each adjacent pair.
    for i in range(6):
        j = (i + 1) % 6
        ax = cx + r * math.cos((2 * math.pi * i / 6) - math.pi / 2)
        ay = cy + r * math.sin((2 * math.pi * i / 6) - math.pi / 2)
        bx = cx + r * math.cos((2 * math.pi * j / 6) - math.pi / 2)
        by = cy + r * math.sin((2 * math.pi * j / 6) - math.pi / 2)
        suns_list.append(_sun(sid, (ax + bx) / 2, (ay + by) / 2, NEUTRAL, ng))
        sid += 1

    # Inner ring of neutrals (halfway to centre).
    inner_r = r * 0.45
    for i in range(6):
        angle = 2 * math.pi * i / 6  # offset from player positions
        x = cx + inner_r * math.cos(angle)
        y = cy + inner_r * math.sin(angle)
        suns_list.append(_sun(sid, x, y, NEUTRAL, ng))
        sid += 1

    # Centre.
    suns_list.append(_sun(sid, cx, cy, NEUTRAL, ng * 2))

    return GameState(suns=dict(suns_list), players=players)
