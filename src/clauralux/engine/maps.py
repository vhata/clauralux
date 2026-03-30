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


# ── Fun / themed maps (2-player) ────────────────────────────────────────


def the_grid(config: GameConfig) -> GameState:
    """A 5x4 grid of suns. Players start in opposite corners. Control the lines."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    cols, rows = 5, 4
    suns_list: list[tuple[SunId, Sun]] = []
    sid = 0
    for row in range(rows):
        for col in range(cols):
            x = w * (0.1 + 0.8 * col / (cols - 1))
            y = h * (0.15 + 0.7 * row / (rows - 1))
            if row == 0 and col == 0:
                suns_list.append(_sun(sid, x, y, p1, g))
            elif row == rows - 1 and col == cols - 1:
                suns_list.append(_sun(sid, x, y, p2, g))
            else:
                suns_list.append(_sun(sid, x, y, NEUTRAL, ng))
            sid += 1

    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_fortress(config: GameConfig) -> GameState:
    """A heavily fortified center sun surrounded by a ring. Players start far out."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison
    cx, cy = w * 0.5, h * 0.5

    suns_list: list[tuple[SunId, Sun]] = [
        _sun(0, w * 0.05, h * 0.5, p1, g),
        _sun(1, w * 0.95, h * 0.5, p2, g),
        _sun(2, cx, cy, NEUTRAL, ng * 4),  # the fortress — huge garrison
    ]
    sid = 3
    # Ring of suns around the fortress.
    for i in range(8):
        angle = 2 * math.pi * i / 8
        x = cx + min(w, h) * 0.22 * math.cos(angle)
        y = cy + min(w, h) * 0.22 * math.sin(angle)
        suns_list.append(_sun(sid, x, y, NEUTRAL, ng))
        sid += 1

    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_bridge(config: GameConfig) -> GameState:
    """Two clusters connected by a narrow chain of suns. Control the bridge."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns_list: list[tuple[SunId, Sun]] = [
        # P1 cluster (left).
        _sun(0, w * 0.1, h * 0.5, p1, g),
        _sun(1, w * 0.15, h * 0.3, NEUTRAL, ng),
        _sun(2, w * 0.15, h * 0.7, NEUTRAL, ng),
        _sun(3, w * 0.22, h * 0.5, NEUTRAL, ng),
        # Bridge (center chain).
        _sun(4, w * 0.37, h * 0.5, NEUTRAL, ng * 1.5),
        _sun(5, w * 0.5, h * 0.5, NEUTRAL, ng * 2),
        _sun(6, w * 0.63, h * 0.5, NEUTRAL, ng * 1.5),
        # P2 cluster (right).
        _sun(7, w * 0.78, h * 0.5, NEUTRAL, ng),
        _sun(8, w * 0.85, h * 0.3, NEUTRAL, ng),
        _sun(9, w * 0.85, h * 0.7, NEUTRAL, ng),
        _sun(10, w * 0.9, h * 0.5, p2, g),
    ]
    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_ring(config: GameConfig) -> GameState:
    """Suns arranged in a circle. Players start opposite. Expand clockwise or counter?"""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison
    cx, cy = w * 0.5, h * 0.5
    r = min(w, h) * 0.35
    n_suns = 12

    suns_list: list[tuple[SunId, Sun]] = []
    for i in range(n_suns):
        angle = 2 * math.pi * i / n_suns - math.pi / 2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        if i == 0:
            suns_list.append(_sun(i, x, y, p1, g))
        elif i == n_suns // 2:
            suns_list.append(_sun(i, x, y, p2, g))
        else:
            suns_list.append(_sun(i, x, y, NEUTRAL, ng))

    # Juicy center prize.
    suns_list.append(_sun(n_suns, cx, cy, NEUTRAL, ng * 3))

    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_corridor(config: GameConfig) -> GameState:
    """Long narrow map — two rows of suns. A head-to-head slugfest."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns_list: list[tuple[SunId, Sun]] = []
    sid = 0
    cols = 7
    for col in range(cols):
        x = w * (0.08 + 0.84 * col / (cols - 1))
        for row_y in [h * 0.35, h * 0.65]:
            if col == 0 and row_y < h * 0.5:
                suns_list.append(_sun(sid, x, row_y, p1, g))
            elif col == cols - 1 and row_y > h * 0.5:
                suns_list.append(_sun(sid, x, row_y, p2, g))
            else:
                suns_list.append(_sun(sid, x, row_y, NEUTRAL, ng))
            sid += 1

    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_archipelago(config: GameConfig) -> GameState:
    """Clusters of suns with gaps between. Leap between islands."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns_list: list[tuple[SunId, Sun]] = [
        # P1 island (top-left).
        _sun(0, w * 0.1, h * 0.2, p1, g),
        _sun(1, w * 0.18, h * 0.12, NEUTRAL, ng),
        _sun(2, w * 0.18, h * 0.28, NEUTRAL, ng),
        # Central island (contested).
        _sun(3, w * 0.45, h * 0.45, NEUTRAL, ng * 1.5),
        _sun(4, w * 0.55, h * 0.45, NEUTRAL, ng * 1.5),
        _sun(5, w * 0.45, h * 0.55, NEUTRAL, ng * 1.5),
        _sun(6, w * 0.55, h * 0.55, NEUTRAL, ng * 1.5),
        # Side islands.
        _sun(7, w * 0.15, h * 0.7, NEUTRAL, ng),
        _sun(8, w * 0.85, h * 0.3, NEUTRAL, ng),
        # P2 island (bottom-right).
        _sun(9, w * 0.9, h * 0.8, p2, g),
        _sun(10, w * 0.82, h * 0.72, NEUTRAL, ng),
        _sun(11, w * 0.82, h * 0.88, NEUTRAL, ng),
    ]
    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_spiral(config: GameConfig) -> GameState:
    """Suns spiraling outward from center. Race inward or outward?"""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison
    cx, cy = w * 0.5, h * 0.5

    suns_list: list[tuple[SunId, Sun]] = []
    n_suns = 14
    for i in range(n_suns):
        t = i / (n_suns - 1)
        angle = t * 3 * math.pi  # ~1.5 turns
        r = min(w, h) * (0.05 + 0.35 * t)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        if i == 0:
            # Center — heavily fortified neutral.
            suns_list.append(_sun(i, x, y, NEUTRAL, ng * 3))
        elif i == 1:
            suns_list.append(_sun(i, x, y, p1, g))
        elif i == n_suns - 1:
            suns_list.append(_sun(i, x, y, p2, g))
        else:
            suns_list.append(_sun(i, x, y, NEUTRAL, ng))

    return GameState(suns=dict(suns_list), players=[p1, p2])


def the_diamond(config: GameConfig) -> GameState:
    """Diamond shape — players at left/right tips, fortified center."""
    p1, p2 = PlayerId(1), PlayerId(2)
    w, h = config.map_width, config.map_height
    g, ng = config.default_player_garrison, config.default_neutral_garrison

    suns_list: list[tuple[SunId, Sun]] = [
        # Tips.
        _sun(0, w * 0.05, h * 0.5, p1, g),
        _sun(1, w * 0.95, h * 0.5, p2, g),
        # Top and bottom points.
        _sun(2, w * 0.5, h * 0.1, NEUTRAL, ng),
        _sun(3, w * 0.5, h * 0.9, NEUTRAL, ng),
        # Inner diamond.
        _sun(4, w * 0.25, h * 0.3, NEUTRAL, ng),
        _sun(5, w * 0.25, h * 0.7, NEUTRAL, ng),
        _sun(6, w * 0.75, h * 0.3, NEUTRAL, ng),
        _sun(7, w * 0.75, h * 0.7, NEUTRAL, ng),
        # Center.
        _sun(8, w * 0.5, h * 0.5, NEUTRAL, ng * 2.5),
        # Mid flanks.
        _sun(9, w * 0.35, h * 0.5, NEUTRAL, ng),
        _sun(10, w * 0.65, h * 0.5, NEUTRAL, ng),
    ]
    return GameState(suns=dict(suns_list), players=[p1, p2])
