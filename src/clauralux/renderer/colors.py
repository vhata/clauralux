from __future__ import annotations

from clauralux.engine.types import NEUTRAL, PlayerId

# RGB tuples.
BACKGROUND = (10, 10, 20)
GRID_LINE = (25, 25, 40)
TEXT = (200, 200, 200)
TEXT_DIM = (120, 120, 120)

# Player colours: index 0 = neutral, then player 1, 2, 3, ...
PLAYER_COLORS: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (100, 100, 100),
    PlayerId(1): (80, 160, 255),  # blue
    PlayerId(2): (255, 80, 80),  # red
    PlayerId(3): (80, 255, 120),  # green
    PlayerId(4): (255, 200, 60),  # yellow
    PlayerId(5): (200, 100, 255),  # purple
    PlayerId(6): (255, 160, 80),  # orange
}

# Brighter versions for highlights / unit groups.
PLAYER_COLORS_BRIGHT: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (140, 140, 140),
    PlayerId(1): (130, 200, 255),
    PlayerId(2): (255, 130, 130),
    PlayerId(3): (130, 255, 170),
    PlayerId(4): (255, 230, 120),
    PlayerId(5): (230, 160, 255),
    PlayerId(6): (255, 200, 130),
}


def get_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS.get(player_id, (180, 180, 180))


def get_bright_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS_BRIGHT.get(player_id, (220, 220, 220))
