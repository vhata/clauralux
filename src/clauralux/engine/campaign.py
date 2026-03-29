from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .config import GameConfig
from .state import GameState, Sun
from .types import NEUTRAL, PlayerId, Position, SunId


@dataclass(frozen=True, slots=True)
class CampaignLevel:
    """A single campaign level definition."""

    name: str
    description: str
    map_factory: Callable[[GameConfig], GameState]
    config_overrides: dict[str, Any]
    enemy_bots: dict[PlayerId, str]  # enemies only; P1 is chosen by user


def _make_sun(
    sun_id: int, x: float, y: float, owner: PlayerId, garrison: float, level: int = 1
) -> tuple[SunId, Sun]:
    sid = SunId(sun_id)
    return sid, Sun(id=sid, position=Position(x, y), owner=owner, garrison=garrison, level=level)


# --- Level map factories ---
# All use relative positioning on the default 1000x800 map.

P1 = PlayerId(1)
P2 = PlayerId(2)
P3 = PlayerId(3)


def _level_01(config: GameConfig) -> GameState:
    """Easy start: player near 3 neutrals, enemy far away."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.15, h * 0.5, P1, 10),
            _make_sun(1, w * 0.85, h * 0.5, P2, 3),
            _make_sun(2, w * 0.3, h * 0.3, NEUTRAL, 3),
            _make_sun(3, w * 0.3, h * 0.5, NEUTRAL, 3),
            _make_sun(4, w * 0.3, h * 0.7, NEUTRAL, 3),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_02(config: GameConfig) -> GameState:
    """Symmetric 1v1, 3 neutrals."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.15, h * 0.5, P1, 5),
            _make_sun(1, w * 0.85, h * 0.5, P2, 5),
            _make_sun(2, w * 0.5, h * 0.2, NEUTRAL, 5),
            _make_sun(3, w * 0.5, h * 0.5, NEUTRAL, 5),
            _make_sun(4, w * 0.5, h * 0.8, NEUTRAL, 5),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_03(config: GameConfig) -> GameState:
    """Open map, 5 neutrals, vs random."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.1, h * 0.5, P1, 5),
            _make_sun(1, w * 0.9, h * 0.5, P2, 5),
            _make_sun(2, w * 0.35, h * 0.25, NEUTRAL, 6),
            _make_sun(3, w * 0.35, h * 0.75, NEUTRAL, 6),
            _make_sun(4, w * 0.5, h * 0.5, NEUTRAL, 8),
            _make_sun(5, w * 0.65, h * 0.25, NEUTRAL, 6),
            _make_sun(6, w * 0.65, h * 0.75, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_04(config: GameConfig) -> GameState:
    """Slight positional edge for player, 4 neutrals."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.2, h * 0.5, P1, 5),
            _make_sun(1, w * 0.85, h * 0.5, P2, 5),
            _make_sun(2, w * 0.35, h * 0.3, NEUTRAL, 5),
            _make_sun(3, w * 0.35, h * 0.7, NEUTRAL, 5),
            _make_sun(4, w * 0.6, h * 0.3, NEUTRAL, 8),
            _make_sun(5, w * 0.6, h * 0.7, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_05(config: GameConfig) -> GameState:
    """Fair symmetric fight, 3 neutrals."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.2, h * 0.5, P1, 5),
            _make_sun(1, w * 0.8, h * 0.5, P2, 5),
            _make_sun(2, w * 0.5, h * 0.2, NEUTRAL, 8),
            _make_sun(3, w * 0.5, h * 0.5, NEUTRAL, 10),
            _make_sun(4, w * 0.5, h * 0.8, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_06(config: GameConfig) -> GameState:
    """5 neutrals, spread out. First expander opponent."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.1, h * 0.5, P1, 5),
            _make_sun(1, w * 0.9, h * 0.5, P2, 5),
            _make_sun(2, w * 0.3, h * 0.2, NEUTRAL, 8),
            _make_sun(3, w * 0.3, h * 0.8, NEUTRAL, 8),
            _make_sun(4, w * 0.5, h * 0.5, NEUTRAL, 10),
            _make_sun(5, w * 0.7, h * 0.2, NEUTRAL, 8),
            _make_sun(6, w * 0.7, h * 0.8, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_07(config: GameConfig) -> GameState:
    """Close quarters, 4 neutrals, fast production."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.3, h * 0.5, P1, 5),
            _make_sun(1, w * 0.7, h * 0.5, P2, 5),
            _make_sun(2, w * 0.4, h * 0.3, NEUTRAL, 6),
            _make_sun(3, w * 0.4, h * 0.7, NEUTRAL, 6),
            _make_sun(4, w * 0.6, h * 0.3, NEUTRAL, 6),
            _make_sun(5, w * 0.6, h * 0.7, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_08(config: GameConfig) -> GameState:
    """Large map, 6 neutrals, economic game."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.05, h * 0.5, P1, 5),
            _make_sun(1, w * 0.95, h * 0.5, P2, 5),
            _make_sun(2, w * 0.25, h * 0.2, NEUTRAL, 10),
            _make_sun(3, w * 0.25, h * 0.8, NEUTRAL, 10),
            _make_sun(4, w * 0.5, h * 0.35, NEUTRAL, 15),
            _make_sun(5, w * 0.5, h * 0.65, NEUTRAL, 15),
            _make_sun(6, w * 0.75, h * 0.2, NEUTRAL, 10),
            _make_sun(7, w * 0.75, h * 0.8, NEUTRAL, 10),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_09(config: GameConfig) -> GameState:
    """Comeback: enemy starts with 2 suns."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.1, h * 0.5, P1, 5),
            _make_sun(1, w * 0.7, h * 0.3, P2, 5),
            _make_sun(2, w * 0.7, h * 0.7, P2, 5),
            _make_sun(3, w * 0.35, h * 0.3, NEUTRAL, 8),
            _make_sun(4, w * 0.35, h * 0.7, NEUTRAL, 8),
            _make_sun(5, w * 0.5, h * 0.5, NEUTRAL, 12),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_10(config: GameConfig) -> GameState:
    """First aggressive opponent, tight map."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.25, h * 0.5, P1, 5),
            _make_sun(1, w * 0.75, h * 0.5, P2, 5),
            _make_sun(2, w * 0.5, h * 0.3, NEUTRAL, 8),
            _make_sun(3, w * 0.5, h * 0.5, NEUTRAL, 10),
            _make_sun(4, w * 0.5, h * 0.7, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_11(config: GameConfig) -> GameState:
    """Standard aggressive, 5 neutrals."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.15, h * 0.5, P1, 5),
            _make_sun(1, w * 0.85, h * 0.5, P2, 5),
            _make_sun(2, w * 0.35, h * 0.2, NEUTRAL, 10),
            _make_sun(3, w * 0.35, h * 0.8, NEUTRAL, 10),
            _make_sun(4, w * 0.5, h * 0.5, NEUTRAL, 12),
            _make_sun(5, w * 0.65, h * 0.2, NEUTRAL, 10),
            _make_sun(6, w * 0.65, h * 0.8, NEUTRAL, 10),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_12(config: GameConfig) -> GameState:
    """First 1v2: outnumbered but weak enemies."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.1, P1, 8),
            _make_sun(1, w * 0.15, h * 0.85, P2, 3),
            _make_sun(2, w * 0.85, h * 0.85, P3, 3),
            _make_sun(3, w * 0.3, h * 0.4, NEUTRAL, 5),
            _make_sun(4, w * 0.7, h * 0.4, NEUTRAL, 5),
            _make_sun(5, w * 0.5, h * 0.6, NEUTRAL, 8),
            _make_sun(6, w * 0.5, h * 0.85, NEUTRAL, 5),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_13(config: GameConfig) -> GameState:
    """1v2: moderate enemies, 6 neutrals."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.1, P1, 5),
            _make_sun(1, w * 0.1, h * 0.9, P2, 5),
            _make_sun(2, w * 0.9, h * 0.9, P3, 5),
            _make_sun(3, w * 0.25, h * 0.35, NEUTRAL, 8),
            _make_sun(4, w * 0.75, h * 0.35, NEUTRAL, 8),
            _make_sun(5, w * 0.5, h * 0.5, NEUTRAL, 10),
            _make_sun(6, w * 0.3, h * 0.7, NEUTRAL, 8),
            _make_sun(7, w * 0.7, h * 0.7, NEUTRAL, 8),
            _make_sun(8, w * 0.5, h * 0.85, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_14(config: GameConfig) -> GameState:
    """1v2: tough duo of expanders."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.15, P1, 5),
            _make_sun(1, w * 0.15, h * 0.85, P2, 5),
            _make_sun(2, w * 0.85, h * 0.85, P3, 5),
            _make_sun(3, w * 0.3, h * 0.4, NEUTRAL, 10),
            _make_sun(4, w * 0.7, h * 0.4, NEUTRAL, 10),
            _make_sun(5, w * 0.5, h * 0.55, NEUTRAL, 12),
            _make_sun(6, w * 0.35, h * 0.7, NEUTRAL, 8),
            _make_sun(7, w * 0.65, h * 0.7, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_15(config: GameConfig) -> GameState:
    """1v2: tight, real pressure."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.2, P1, 5),
            _make_sun(1, w * 0.2, h * 0.8, P2, 5),
            _make_sun(2, w * 0.8, h * 0.8, P3, 5),
            _make_sun(3, w * 0.35, h * 0.45, NEUTRAL, 8),
            _make_sun(4, w * 0.65, h * 0.45, NEUTRAL, 8),
            _make_sun(5, w * 0.5, h * 0.65, NEUTRAL, 10),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_16(config: GameConfig) -> GameState:
    """Hard 1v1: enemy has positional advantage."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.1, h * 0.5, P1, 5),
            _make_sun(1, w * 0.6, h * 0.5, P2, 5),
            _make_sun(2, w * 0.35, h * 0.3, NEUTRAL, 12),
            _make_sun(3, w * 0.35, h * 0.7, NEUTRAL, 12),
            _make_sun(4, w * 0.8, h * 0.3, NEUTRAL, 6),
            _make_sun(5, w * 0.8, h * 0.7, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_17(config: GameConfig) -> GameState:
    """Hard 1v2: large map, strong enemies."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.1, P1, 5),
            _make_sun(1, w * 0.1, h * 0.9, P2, 5),
            _make_sun(2, w * 0.9, h * 0.9, P3, 5),
            _make_sun(3, w * 0.2, h * 0.35, NEUTRAL, 10),
            _make_sun(4, w * 0.8, h * 0.35, NEUTRAL, 10),
            _make_sun(5, w * 0.5, h * 0.4, NEUTRAL, 12),
            _make_sun(6, w * 0.35, h * 0.65, NEUTRAL, 10),
            _make_sun(7, w * 0.65, h * 0.65, NEUTRAL, 10),
            _make_sun(8, w * 0.5, h * 0.85, NEUTRAL, 8),
            _make_sun(9, w * 0.3, h * 0.85, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_18(config: GameConfig) -> GameState:
    """Boss fight: 1v2, few neutrals, close, aggressive enemies."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _make_sun(0, w * 0.5, h * 0.15, P1, 5),
            _make_sun(1, w * 0.25, h * 0.75, P2, 8),
            _make_sun(2, w * 0.75, h * 0.75, P3, 8),
            _make_sun(3, w * 0.5, h * 0.45, NEUTRAL, 10),
            _make_sun(4, w * 0.35, h * 0.55, NEUTRAL, 8),
            _make_sun(5, w * 0.65, h * 0.55, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


# --- Campaign level list ---

CAMPAIGN_LEVELS: list[CampaignLevel] = [
    CampaignLevel(
        name="First Light",
        description="An easy start. You have the advantage.",
        map_factory=_level_01,
        config_overrides={},
        enemy_bots={P2: "passive"},
    ),
    CampaignLevel(
        name="Even Ground",
        description="A fair fight against a passive opponent.",
        map_factory=_level_02,
        config_overrides={},
        enemy_bots={P2: "passive"},
    ),
    CampaignLevel(
        name="Open Field",
        description="More room to manoeuvre. The enemy is unpredictable.",
        map_factory=_level_03,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    CampaignLevel(
        name="Forward Position",
        description="You have a slight edge. Use it wisely.",
        map_factory=_level_04,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    CampaignLevel(
        name="Mirror Match",
        description="No advantages here. Outplay a random opponent.",
        map_factory=_level_05,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    CampaignLevel(
        name="The Expander",
        description="Your opponent knows how to grow. So should you.",
        map_factory=_level_06,
        config_overrides={},
        enemy_bots={P2: "expander"},
    ),
    CampaignLevel(
        name="Close Quarters",
        description="Tight spaces, fast production. No time to think.",
        map_factory=_level_07,
        config_overrides={"production_interval": 20},
        enemy_bots={P2: "expander"},
    ),
    CampaignLevel(
        name="The Long Game",
        description="A vast map. Economy wins here.",
        map_factory=_level_08,
        config_overrides={"production_interval": 40},
        enemy_bots={P2: "expander"},
    ),
    CampaignLevel(
        name="Comeback",
        description="They start with two suns. You start with grit.",
        map_factory=_level_09,
        config_overrides={},
        enemy_bots={P2: "expander"},
    ),
    CampaignLevel(
        name="Blitz",
        description="The enemy attacks fast and hard. Be ready.",
        map_factory=_level_10,
        config_overrides={},
        enemy_bots={P2: "aggressive"},
    ),
    CampaignLevel(
        name="Siege",
        description="A standard battle against an aggressive foe.",
        map_factory=_level_11,
        config_overrides={},
        enemy_bots={P2: "aggressive"},
    ),
    CampaignLevel(
        name="Two Fronts",
        description="Outnumbered but not outgunned. They're weak.",
        map_factory=_level_12,
        config_overrides={},
        enemy_bots={P2: "passive", P3: "random"},
    ),
    CampaignLevel(
        name="Pincer",
        description="Two enemies, growing smarter.",
        map_factory=_level_13,
        config_overrides={},
        enemy_bots={P2: "random", P3: "expander"},
    ),
    CampaignLevel(
        name="Double Trouble",
        description="Two expanders. They'll outgrow you if you let them.",
        map_factory=_level_14,
        config_overrides={},
        enemy_bots={P2: "expander", P3: "expander"},
    ),
    CampaignLevel(
        name="Pressure Cooker",
        description="Tight map, serious pressure from two directions.",
        map_factory=_level_15,
        config_overrides={},
        enemy_bots={P2: "expander", P3: "aggressive"},
    ),
    CampaignLevel(
        name="Uphill Battle",
        description="The enemy holds the centre. Take it from them.",
        map_factory=_level_16,
        config_overrides={},
        enemy_bots={P2: "aggressive"},
    ),
    CampaignLevel(
        name="Gauntlet",
        description="A large battlefield with two strong enemies.",
        map_factory=_level_17,
        config_overrides={},
        enemy_bots={P2: "aggressive", P3: "expander"},
    ),
    CampaignLevel(
        name="Final Stand",
        description="Two aggressive enemies. Close quarters. Good luck.",
        map_factory=_level_18,
        config_overrides={"production_interval": 20},
        enemy_bots={P2: "aggressive", P3: "aggressive"},
    ),
]
