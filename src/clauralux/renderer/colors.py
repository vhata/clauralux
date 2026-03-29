from __future__ import annotations

from clauralux.engine.types import NEUTRAL, PlayerId

# RGB tuples.
BACKGROUND = (10, 10, 20)
GRID_LINE = (25, 25, 40)
TEXT = (200, 200, 200)
TEXT_DIM = (120, 120, 120)

# Player colours — chosen for maximum contrast against dark background
# and against each other. Well-spaced around the hue wheel, high saturation.
PLAYER_COLORS: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (90, 90, 100),
    PlayerId(1): (50, 140, 255),  # vivid blue
    PlayerId(2): (255, 55, 55),  # bright red
    PlayerId(3): (30, 220, 70),  # saturated green
    PlayerId(4): (255, 220, 40),  # golden yellow
    PlayerId(5): (220, 50, 255),  # magenta/violet
    PlayerId(6): (255, 140, 30),  # deep orange
}

# Brighter versions for unit groups — more white mixed in.
PLAYER_COLORS_BRIGHT: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (140, 140, 150),
    PlayerId(1): (120, 180, 255),
    PlayerId(2): (255, 120, 120),
    PlayerId(3): (100, 255, 140),
    PlayerId(4): (255, 240, 120),
    PlayerId(5): (240, 130, 255),
    PlayerId(6): (255, 180, 100),
}


def get_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS.get(player_id, (180, 180, 180))


def get_bright_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS_BRIGHT.get(player_id, (220, 220, 220))
