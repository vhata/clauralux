from __future__ import annotations

from clauralux.engine.types import NEUTRAL, PlayerId

# RGB tuples.
BACKGROUND = (10, 10, 20)
GRID_LINE = (25, 25, 40)
TEXT = (200, 200, 200)
TEXT_DIM = (120, 120, 120)

# Player colours — chosen for maximum contrast against dark background
# and against each other. Well-spaced around the hue wheel, high saturation.
_DEFAULT_COLORS: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (90, 90, 100),
    PlayerId(1): (50, 140, 255),  # vivid blue
    PlayerId(2): (255, 55, 55),  # bright red
    PlayerId(3): (30, 220, 70),  # saturated green
    PlayerId(4): (255, 220, 40),  # golden yellow
    PlayerId(5): (220, 50, 255),  # magenta/violet
    PlayerId(6): (255, 140, 30),  # deep orange
}

_DEFAULT_BRIGHT: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (140, 140, 150),
    PlayerId(1): (120, 180, 255),
    PlayerId(2): (255, 120, 120),
    PlayerId(3): (100, 255, 140),
    PlayerId(4): (255, 240, 120),
    PlayerId(5): (240, 130, 255),
    PlayerId(6): (255, 180, 100),
}

# Colorblind-safe palette — avoids red-green confusion.
# Based on Wong (2011) palette, adapted for dark background.
_COLORBLIND_COLORS: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (90, 90, 100),
    PlayerId(1): (0, 114, 178),  # blue
    PlayerId(2): (230, 159, 0),  # orange
    PlayerId(3): (86, 180, 233),  # sky blue
    PlayerId(4): (240, 228, 66),  # yellow
    PlayerId(5): (204, 121, 167),  # reddish purple
    PlayerId(6): (0, 158, 115),  # bluish green
}

_COLORBLIND_BRIGHT: dict[PlayerId, tuple[int, int, int]] = {
    NEUTRAL: (140, 140, 150),
    PlayerId(1): (80, 160, 220),
    PlayerId(2): (255, 190, 80),
    PlayerId(3): (140, 210, 255),
    PlayerId(4): (255, 245, 130),
    PlayerId(5): (230, 170, 200),
    PlayerId(6): (80, 200, 165),
}

# Active palette — switch via set_colorblind_mode().
PLAYER_COLORS: dict[PlayerId, tuple[int, int, int]] = dict(_DEFAULT_COLORS)
PLAYER_COLORS_BRIGHT: dict[PlayerId, tuple[int, int, int]] = dict(_DEFAULT_BRIGHT)


def set_colorblind_mode(enabled: bool) -> None:
    """Switch between default and colorblind-safe colour palettes."""
    source = _COLORBLIND_COLORS if enabled else _DEFAULT_COLORS
    bright = _COLORBLIND_BRIGHT if enabled else _DEFAULT_BRIGHT
    PLAYER_COLORS.clear()
    PLAYER_COLORS.update(source)
    PLAYER_COLORS_BRIGHT.clear()
    PLAYER_COLORS_BRIGHT.update(bright)


def get_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS.get(player_id, (180, 180, 180))


def get_bright_color(player_id: PlayerId) -> tuple[int, int, int]:
    return PLAYER_COLORS_BRIGHT.get(player_id, (220, 220, 220))
