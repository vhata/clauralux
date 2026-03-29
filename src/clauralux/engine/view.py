from __future__ import annotations

from dataclasses import dataclass

from .config import GameConfig
from .state import GameState
from .types import NEUTRAL, PlayerId, Position, SunId, Tick


@dataclass(frozen=True, slots=True)
class SunView:
    """Immutable view of a sun, as seen by a bot."""

    id: SunId
    position: Position
    owner: PlayerId
    level: int
    garrison: int  # floor of the internal float — no fractional info leaked


@dataclass(frozen=True, slots=True)
class UnitGroupView:
    """Immutable view of a unit group in transit."""

    owner: PlayerId
    count: int
    position: Position
    target_sun_id: SunId


@dataclass(frozen=True, slots=True)
class GameView:
    """Immutable snapshot of the game, provided to bots each decision tick."""

    my_id: PlayerId
    tick: Tick
    suns: tuple[SunView, ...]
    unit_groups: tuple[UnitGroupView, ...]
    config: GameConfig
    players: tuple[PlayerId, ...]
    eliminated: frozenset[PlayerId]

    def my_suns(self) -> tuple[SunView, ...]:
        return tuple(s for s in self.suns if s.owner == self.my_id)

    def enemy_suns(self) -> tuple[SunView, ...]:
        return tuple(s for s in self.suns if s.owner != self.my_id and s.owner != NEUTRAL)

    def neutral_suns(self) -> tuple[SunView, ...]:
        return tuple(s for s in self.suns if s.owner == NEUTRAL)

    def sun_by_id(self, sun_id: SunId) -> SunView | None:
        for s in self.suns:
            if s.id == sun_id:
                return s
        return None

    def my_unit_groups(self) -> tuple[UnitGroupView, ...]:
        return tuple(g for g in self.unit_groups if g.owner == self.my_id)

    def enemy_unit_groups(self) -> tuple[UnitGroupView, ...]:
        return tuple(g for g in self.unit_groups if g.owner != self.my_id and g.owner != NEUTRAL)

    @staticmethod
    def from_state(state: GameState, player_id: PlayerId, config: GameConfig) -> GameView:
        """Build a GameView snapshot from the mutable GameState."""
        sun_views = tuple(
            SunView(
                id=sun.id,
                position=sun.position,
                owner=sun.owner,
                level=sun.level,
                garrison=int(sun.garrison),
            )
            for sun in state.suns.values()
        )
        group_views = tuple(
            UnitGroupView(
                owner=g.owner,
                count=g.count,
                position=g.position,
                target_sun_id=g.target_sun_id,
            )
            for g in state.unit_groups
        )
        return GameView(
            my_id=player_id,
            tick=state.tick,
            suns=sun_views,
            unit_groups=group_views,
            config=config,
            players=tuple(state.players),
            eliminated=frozenset(state.eliminated),
        )
