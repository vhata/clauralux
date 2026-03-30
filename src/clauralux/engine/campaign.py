"""Campaign level definitions — 24 levels across 4 acts.

Each level introduces a concept or opponent type, with descriptions that teach
the player what to expect and how to counter it. Designed to be played with
the human bot as P1.
"""

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


def _sun(
    sun_id: int, x: float, y: float, owner: PlayerId, garrison: float, level: int = 1
) -> tuple[SunId, Sun]:
    sid = SunId(sun_id)
    return sid, Sun(id=sid, position=Position(x, y), owner=owner, garrison=garrison, level=level)


P1 = PlayerId(1)
P2 = PlayerId(2)
P3 = PlayerId(3)


# ── Act 1: Learning the Basics (Levels 1-6) ─────────────────────────────


def _level_01(config: GameConfig) -> GameState:
    """Tutorial: you + 3 easy neutrals, passive enemy far away."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, P1, 10),
            _sun(1, w * 0.85, h * 0.5, P2, 3),
            _sun(2, w * 0.3, h * 0.3, NEUTRAL, 2),
            _sun(3, w * 0.3, h * 0.5, NEUTRAL, 2),
            _sun(4, w * 0.3, h * 0.7, NEUTRAL, 2),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_02(config: GameConfig) -> GameState:
    """Slow production — must upgrade to win."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 8),
            _sun(1, w * 0.8, h * 0.5, P2, 3),
            _sun(2, w * 0.4, h * 0.3, NEUTRAL, 3),
            _sun(3, w * 0.4, h * 0.7, NEUTRAL, 3),
            _sun(4, w * 0.6, h * 0.5, NEUTRAL, 5),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_03(config: GameConfig) -> GameState:
    """Enemy has 2 suns — learn to attack and capture enemy territory."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, P1, 8),
            _sun(1, w * 0.7, h * 0.3, P2, 3),
            _sun(2, w * 0.7, h * 0.7, P2, 3),
            _sun(3, w * 0.4, h * 0.5, NEUTRAL, 4),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_04(config: GameConfig) -> GameState:
    """First real opponent: chaotic but can surprise you."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, P1, 5),
            _sun(1, w * 0.85, h * 0.5, P2, 5),
            _sun(2, w * 0.4, h * 0.3, NEUTRAL, 5),
            _sun(3, w * 0.4, h * 0.7, NEUTRAL, 5),
            _sun(4, w * 0.6, h * 0.3, NEUTRAL, 5),
            _sun(5, w * 0.6, h * 0.7, NEUTRAL, 5),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_05(config: GameConfig) -> GameState:
    """Many neutrals — race to expand."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.1, h * 0.5, P1, 5),
            _sun(1, w * 0.9, h * 0.5, P2, 5),
            _sun(2, w * 0.25, h * 0.2, NEUTRAL, 4),
            _sun(3, w * 0.25, h * 0.8, NEUTRAL, 4),
            _sun(4, w * 0.4, h * 0.5, NEUTRAL, 5),
            _sun(5, w * 0.6, h * 0.5, NEUTRAL, 5),
            _sun(6, w * 0.75, h * 0.2, NEUTRAL, 4),
            _sun(7, w * 0.75, h * 0.8, NEUTRAL, 4),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_06(config: GameConfig) -> GameState:
    """Enemy closer to center — must defend what you take."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.1, h * 0.5, P1, 5),
            _sun(1, w * 0.6, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.3, NEUTRAL, 6),
            _sun(3, w * 0.35, h * 0.7, NEUTRAL, 6),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


# ── Act 2: Meeting the Specialists (Levels 7-14) ────────────────────────


def _level_07(config: GameConfig) -> GameState:
    """Close quarters vs rush — constant pressure."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.3, h * 0.5, P1, 5),
            _sun(1, w * 0.7, h * 0.5, P2, 5),
            _sun(2, w * 0.4, h * 0.3, NEUTRAL, 4),
            _sun(3, w * 0.4, h * 0.7, NEUTRAL, 4),
            _sun(4, w * 0.6, h * 0.3, NEUTRAL, 4),
            _sun(5, w * 0.6, h * 0.7, NEUTRAL, 4),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_08(config: GameConfig) -> GameState:
    """Wide map vs expander — many neutrals to contest."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.1, h * 0.5, P1, 5),
            _sun(1, w * 0.9, h * 0.5, P2, 5),
            _sun(2, w * 0.3, h * 0.2, NEUTRAL, 6),
            _sun(3, w * 0.3, h * 0.8, NEUTRAL, 6),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 8),
            _sun(5, w * 0.7, h * 0.2, NEUTRAL, 6),
            _sun(6, w * 0.7, h * 0.8, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_09(config: GameConfig) -> GameState:
    """Slow production vs turtle — attack before they snowball."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.4, h * 0.3, NEUTRAL, 8),
            _sun(3, w * 0.4, h * 0.7, NEUTRAL, 8),
            _sun(4, w * 0.6, h * 0.3, NEUTRAL, 8),
            _sun(5, w * 0.6, h * 0.7, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_10(config: GameConfig) -> GameState:
    """Sniper ignores neutrals and hunts your weakest sun."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.3, P1, 5),
            _sun(1, w * 0.85, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.5, NEUTRAL, 6),
            _sun(3, w * 0.5, h * 0.2, NEUTRAL, 6),
            _sun(4, w * 0.5, h * 0.8, NEUTRAL, 6),
            _sun(5, w * 0.65, h * 0.5, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_11(config: GameConfig) -> GameState:
    """Many suns, constant small attacks from everywhere."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.1, h * 0.5, P1, 5),
            _sun(1, w * 0.9, h * 0.5, P2, 5),
            _sun(2, w * 0.25, h * 0.2, NEUTRAL, 3),
            _sun(3, w * 0.25, h * 0.5, NEUTRAL, 3),
            _sun(4, w * 0.25, h * 0.8, NEUTRAL, 3),
            _sun(5, w * 0.5, h * 0.2, NEUTRAL, 4),
            _sun(6, w * 0.5, h * 0.5, NEUTRAL, 5),
            _sun(7, w * 0.5, h * 0.8, NEUTRAL, 4),
            _sun(8, w * 0.75, h * 0.2, NEUTRAL, 3),
            _sun(9, w * 0.75, h * 0.5, NEUTRAL, 3),
            _sun(10, w * 0.75, h * 0.8, NEUTRAL, 3),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_12(config: GameConfig) -> GameState:
    """Opportunist pounces on any weakness."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.25, NEUTRAL, 6),
            _sun(3, w * 0.35, h * 0.75, NEUTRAL, 6),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 8),
            _sun(5, w * 0.65, h * 0.25, NEUTRAL, 6),
            _sun(6, w * 0.65, h * 0.75, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_13(config: GameConfig) -> GameState:
    """Economic bot upgrades hard, then hits your best suns."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, P1, 5),
            _sun(1, w * 0.85, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.2, NEUTRAL, 8),
            _sun(3, w * 0.35, h * 0.8, NEUTRAL, 8),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 10),
            _sun(5, w * 0.65, h * 0.2, NEUTRAL, 8),
            _sun(6, w * 0.65, h * 0.8, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_14(config: GameConfig) -> GameState:
    """Baiter sends decoys to draw defenders, then strikes weakened suns."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.3, NEUTRAL, 6),
            _sun(3, w * 0.35, h * 0.7, NEUTRAL, 6),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 8),
            _sun(5, w * 0.65, h * 0.3, NEUTRAL, 6),
            _sun(6, w * 0.65, h * 0.7, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


# ── Act 3: Multi-Front Warfare (Levels 15-19) ───────────────────────────


def _level_15(config: GameConfig) -> GameState:
    """First 1v2 — weak enemies, generous position."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.1, P1, 8),
            _sun(1, w * 0.15, h * 0.85, P2, 3),
            _sun(2, w * 0.85, h * 0.85, P3, 3),
            _sun(3, w * 0.3, h * 0.4, NEUTRAL, 4),
            _sun(4, w * 0.7, h * 0.4, NEUTRAL, 4),
            _sun(5, w * 0.5, h * 0.6, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_16(config: GameConfig) -> GameState:
    """1v2: eliminate one before the other grows."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.1, P1, 5),
            _sun(1, w * 0.1, h * 0.9, P2, 5),
            _sun(2, w * 0.9, h * 0.9, P3, 5),
            _sun(3, w * 0.25, h * 0.4, NEUTRAL, 6),
            _sun(4, w * 0.75, h * 0.4, NEUTRAL, 6),
            _sun(5, w * 0.5, h * 0.55, NEUTRAL, 8),
            _sun(6, w * 0.35, h * 0.75, NEUTRAL, 6),
            _sun(7, w * 0.65, h * 0.75, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_17(config: GameConfig) -> GameState:
    """Coordinator accumulates then strikes multiple targets at once."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.4, h * 0.2, NEUTRAL, 8),
            _sun(3, w * 0.4, h * 0.8, NEUTRAL, 8),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 10),
            _sun(5, w * 0.6, h * 0.2, NEUTRAL, 8),
            _sun(6, w * 0.6, h * 0.8, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_18(config: GameConfig) -> GameState:
    """Reactive bot only attacks with overwhelming force. Be patient."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.15, h * 0.5, P1, 5),
            _sun(1, w * 0.85, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.3, NEUTRAL, 10),
            _sun(3, w * 0.35, h * 0.7, NEUTRAL, 10),
            _sun(4, w * 0.65, h * 0.3, NEUTRAL, 10),
            _sun(5, w * 0.65, h * 0.7, NEUTRAL, 10),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_19(config: GameConfig) -> GameState:
    """1v2: rush + expander from two angles."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.15, P1, 5),
            _sun(1, w * 0.15, h * 0.85, P2, 5),
            _sun(2, w * 0.85, h * 0.85, P3, 5),
            _sun(3, w * 0.3, h * 0.45, NEUTRAL, 6),
            _sun(4, w * 0.7, h * 0.45, NEUTRAL, 6),
            _sun(5, w * 0.5, h * 0.65, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


# ── Act 4: The Gauntlet (Levels 20-24) ──────────────────────────────────


def _level_20(config: GameConfig) -> GameState:
    """The evolved bot — trained through thousands of games."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.4, h * 0.25, NEUTRAL, 8),
            _sun(3, w * 0.4, h * 0.75, NEUTRAL, 8),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 10),
            _sun(5, w * 0.6, h * 0.25, NEUTRAL, 8),
            _sun(6, w * 0.6, h * 0.75, NEUTRAL, 8),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_21(config: GameConfig) -> GameState:
    """1v2: aggressive + turtle. Rush the turtle before it snowballs."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.1, P1, 5),
            _sun(1, w * 0.15, h * 0.8, P2, 5),
            _sun(2, w * 0.85, h * 0.8, P3, 5),
            _sun(3, w * 0.3, h * 0.4, NEUTRAL, 8),
            _sun(4, w * 0.7, h * 0.4, NEUTRAL, 8),
            _sun(5, w * 0.5, h * 0.55, NEUTRAL, 10),
            _sun(6, w * 0.4, h * 0.7, NEUTRAL, 6),
            _sun(7, w * 0.6, h * 0.7, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_22(config: GameConfig) -> GameState:
    """1v2: sniper + baiter. Two tricky specialists."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.15, P1, 5),
            _sun(1, w * 0.1, h * 0.85, P2, 5),
            _sun(2, w * 0.9, h * 0.85, P3, 5),
            _sun(3, w * 0.3, h * 0.4, NEUTRAL, 8),
            _sun(4, w * 0.7, h * 0.4, NEUTRAL, 8),
            _sun(5, w * 0.5, h * 0.6, NEUTRAL, 10),
            _sun(6, w * 0.5, h * 0.85, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


def _level_23(config: GameConfig) -> GameState:
    """The neural net bot — adapts its strategy to the board state."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.2, h * 0.5, P1, 5),
            _sun(1, w * 0.8, h * 0.5, P2, 5),
            _sun(2, w * 0.35, h * 0.2, NEUTRAL, 10),
            _sun(3, w * 0.35, h * 0.8, NEUTRAL, 10),
            _sun(4, w * 0.5, h * 0.5, NEUTRAL, 12),
            _sun(5, w * 0.65, h * 0.2, NEUTRAL, 10),
            _sun(6, w * 0.65, h * 0.8, NEUTRAL, 10),
        ]
    )
    return GameState(suns=suns, players=[P1, P2])


def _level_24(config: GameConfig) -> GameState:
    """Final boss: close quarters, two aggressives, fast production."""
    w, h = config.map_width, config.map_height
    suns = dict(
        [
            _sun(0, w * 0.5, h * 0.15, P1, 5),
            _sun(1, w * 0.25, h * 0.75, P2, 8),
            _sun(2, w * 0.75, h * 0.75, P3, 8),
            _sun(3, w * 0.5, h * 0.45, NEUTRAL, 8),
            _sun(4, w * 0.35, h * 0.55, NEUTRAL, 6),
            _sun(5, w * 0.65, h * 0.55, NEUTRAL, 6),
        ]
    )
    return GameState(suns=suns, players=[P1, P2, P3])


# ── Campaign level list ─────────────────────────────────────────────────

CAMPAIGN_LEVELS: list[CampaignLevel] = [
    # Act 1: Learning the Basics
    CampaignLevel(
        name="First Steps",
        description="Click your sun, then click a neutral. The passive enemy won't resist.",
        map_factory=_level_01,
        config_overrides={},
        enemy_bots={P2: "passive"},
    ),
    CampaignLevel(
        name="Growing Your Empire",
        description="Production is slow. Click a sun to upgrade it — higher levels are faster.",
        map_factory=_level_02,
        config_overrides={"production_interval": 50},
        enemy_bots={P2: "passive"},
    ),
    CampaignLevel(
        name="First Blood",
        description="Enemy has two suns. Capture them to win. Hold Shift to send half.",
        map_factory=_level_03,
        config_overrides={},
        enemy_bots={P2: "passive"},
    ),
    CampaignLevel(
        name="The Unpredictable",
        description="This enemy acts randomly — chaotic, but can surprise you. Stay alert.",
        map_factory=_level_04,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    CampaignLevel(
        name="Land Grab",
        description="Many neutrals up for grabs. Whoever expands fastest wins. Move quickly!",
        map_factory=_level_05,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    CampaignLevel(
        name="Holding the Line",
        description="The enemy starts closer to the center. Capture what you can, then defend it.",
        map_factory=_level_06,
        config_overrides={},
        enemy_bots={P2: "random"},
    ),
    # Act 2: Meeting the Specialists
    CampaignLevel(
        name="The Rusher",
        description="Attacks every 20 ticks — relentless. Keep reserves, don't overextend.",
        map_factory=_level_07,
        config_overrides={"production_interval": 15},
        enemy_bots={P2: "rush"},
    ),
    CampaignLevel(
        name="The Expander",
        description="Grabs neutrals fast, upgrades, then attacks. Match pace or strike early.",
        map_factory=_level_08,
        config_overrides={},
        enemy_bots={P2: "expander"},
    ),
    CampaignLevel(
        name="The Turtle",
        description="Upgrades everything to max before attacking. Hit them before they snowball!",
        map_factory=_level_09,
        config_overrides={"production_interval": 50},
        enemy_bots={P2: "turtle"},
    ),
    CampaignLevel(
        name="The Sniper",
        description="Ignores neutrals, targets your weakest sun. Don't leave any sun undefended!",
        map_factory=_level_10,
        config_overrides={"attack_ratio": 0.8},
        enemy_bots={P2: "sniper"},
    ),
    CampaignLevel(
        name="The Swarm",
        description="Tiny attacks from every sun. Death by a thousand cuts. Manage garrisons!",
        map_factory=_level_11,
        config_overrides={"production_interval": 15, "upgrade_costs": (10, 20)},
        enemy_bots={P2: "swarm"},
    ),
    CampaignLevel(
        name="The Opportunist",
        description="Watches for weakness and pounces. Never let your garrisons drop too low.",
        map_factory=_level_12,
        config_overrides={},
        enemy_bots={P2: "opportunist"},
    ),
    CampaignLevel(
        name="The Economist",
        description="Upgrades hard, then targets your best suns. Disrupt their economy!",
        map_factory=_level_13,
        config_overrides={},
        enemy_bots={P2: "economic"},
    ),
    CampaignLevel(
        name="The Baiter",
        description="Sends decoys to draw defenders, then hits the weakened sun. Don't chase!",
        map_factory=_level_14,
        config_overrides={},
        enemy_bots={P2: "baiter"},
    ),
    # Act 3: Multi-Front Warfare
    CampaignLevel(
        name="Two Fronts",
        description="Outnumbered 1v2, but the enemies are weak. Practice fighting on two fronts.",
        map_factory=_level_15,
        config_overrides={},
        enemy_bots={P2: "passive", P3: "random"},
    ),
    CampaignLevel(
        name="Divide and Conquer",
        description="One expands, the other is erratic. Eliminate one before the other grows.",
        map_factory=_level_16,
        config_overrides={},
        enemy_bots={P2: "random", P3: "expander"},
    ),
    CampaignLevel(
        name="The Coordinator",
        description="Accumulates forces, then strikes multiple targets at once. Read the buildup!",
        map_factory=_level_17,
        config_overrides={},
        enemy_bots={P2: "coordinator"},
    ),
    CampaignLevel(
        name="The Reactive",
        description="Reinforces threatened suns, only attacks with overwhelming force. Be patient.",
        map_factory=_level_18,
        config_overrides={},
        enemy_bots={P2: "reactive"},
    ),
    CampaignLevel(
        name="Pincer Movement",
        description="A rusher and an expander from two angles. Survive, then counter-attack.",
        map_factory=_level_19,
        config_overrides={},
        enemy_bots={P2: "rush", P3: "expander"},
    ),
    # Act 4: The Gauntlet
    CampaignLevel(
        name="Evolved Intelligence",
        description="Trained through thousands of games. Everything you've learned, tested.",
        map_factory=_level_20,
        config_overrides={},
        enemy_bots={P2: "evolved"},
    ),
    CampaignLevel(
        name="Double Trouble",
        description="Aggressive and turtle. Rush the turtle before it snowballs — watch your back.",
        map_factory=_level_21,
        config_overrides={},
        enemy_bots={P2: "aggressive", P3: "turtle"},
    ),
    CampaignLevel(
        name="Three-Way War",
        description="A sniper and a baiter. Two of the trickiest specialists, working against you.",
        map_factory=_level_22,
        config_overrides={},
        enemy_bots={P2: "sniper", P3: "baiter"},
    ),
    CampaignLevel(
        name="Neural Warfare",
        description="The neural net bot adapts its strategy to the board state. The ultimate test.",
        map_factory=_level_23,
        config_overrides={},
        enemy_bots={P2: "neural"},
    ),
    CampaignLevel(
        name="Final Stand",
        description="Two aggressive enemies. Close quarters. Fast production. Good luck.",
        map_factory=_level_24,
        config_overrides={"production_interval": 15},
        enemy_bots={P2: "aggressive", P3: "aggressive"},
    ),
]
