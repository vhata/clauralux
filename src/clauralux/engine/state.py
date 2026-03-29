from __future__ import annotations

from dataclasses import dataclass, field

from .types import NEUTRAL, PlayerId, Position, SunId, Tick


@dataclass(slots=True)
class Sun:
    """A sun on the map. Produces units for its owner."""

    id: SunId
    position: Position
    owner: PlayerId = NEUTRAL
    level: int = 1
    garrison: float = 0.0
    # Ticks since last unit was produced. Resets on production and capture.
    production_ticks: int = 0


@dataclass(slots=True)
class UnitGroup:
    """A group of units travelling toward a target sun."""

    owner: PlayerId
    count: int
    position: Position
    target_sun_id: SunId
    # Pre-computed velocity components (set at creation).
    velocity_x: float = 0.0
    velocity_y: float = 0.0


@dataclass(slots=True)
class GameState:
    """The complete mutable state of a game."""

    suns: dict[SunId, Sun] = field(default_factory=dict)
    unit_groups: list[UnitGroup] = field(default_factory=list)
    players: list[PlayerId] = field(default_factory=list)
    tick: Tick = field(default_factory=lambda: Tick(0))
    # None = game in progress, NEUTRAL = draw, otherwise the winning player.
    winner: PlayerId | None = None
    eliminated: set[PlayerId] = field(default_factory=set)
