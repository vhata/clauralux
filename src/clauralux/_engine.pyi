"""Type stubs for the Rust engine extension module."""

from clauralux.engine.types import PlayerId, SunId, Tick

class Position:
    x: float
    y: float
    def __init__(self, x: float, y: float) -> None: ...
    def distance_to(self, other: Position) -> float: ...
    def direction_to(self, other: Position) -> tuple[float, float]: ...

class GameConfig:
    map_width: float
    map_height: float
    production_interval: int
    production_per_level: int
    max_sun_level: int
    upgrade_costs: list[int]
    capture_level_reset: int | None
    unit_speed: float
    attack_ratio: float
    decision_interval: int
    max_ticks: int | None
    ticks_per_second: int
    default_neutral_garrison: float
    default_player_garrison: float
    seed: int | None
    def __init__(
        self,
        map_width: float = 1000.0,
        map_height: float = 800.0,
        production_interval: int = 30,
        production_per_level: int = 1,
        max_sun_level: int = 3,
        upgrade_costs: list[int] | None = None,
        capture_level_reset: int | None = 1,
        unit_speed: float = 2.0,
        attack_ratio: float = 1.0,
        decision_interval: int = 1,
        max_ticks: int | None = 30_000,
        ticks_per_second: int = 50,
        default_neutral_garrison: float = 10.0,
        default_player_garrison: float = 5.0,
        seed: int | None = 42,
    ) -> None: ...
    def replace(self, **kwargs: object) -> GameConfig: ...

class Sun:
    id: SunId
    position: Position
    owner: PlayerId
    level: int
    garrison: float
    production_ticks: int
    def __init__(
        self,
        id: SunId,
        position: Position,
        owner: PlayerId = ...,
        level: int = 1,
        garrison: float = 0.0,
        production_ticks: int = 0,
    ) -> None: ...

class UnitGroup:
    owner: PlayerId
    count: int
    position: Position
    target_sun_id: SunId
    velocity_x: float
    velocity_y: float
    def __init__(
        self,
        owner: PlayerId,
        count: int,
        position: Position,
        target_sun_id: SunId,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
    ) -> None: ...

class GameState:
    suns: dict[SunId, Sun]
    unit_groups: list[UnitGroup]
    players: list[PlayerId]
    tick: Tick
    winner: PlayerId | None
    eliminated: set[PlayerId]
    def __init__(
        self,
        suns: dict[SunId, Sun] | None = None,
        unit_groups: list[UnitGroup] | None = None,
        players: list[PlayerId] | None = None,
        tick: Tick = ...,
        winner: PlayerId | None = None,
        eliminated: set[PlayerId] | None = None,
    ) -> None: ...
    def add_unit_group(self, group: UnitGroup) -> None: ...
    def set_sun(self, id: SunId, sun: Sun) -> None: ...
    def add_eliminated(self, player_id: PlayerId) -> None: ...
    def get_sun(self, id: SunId) -> Sun | None: ...

class SendUnits:
    source_sun_id: SunId
    target_sun_id: SunId
    count: int
    def __init__(self, source_sun_id: SunId, target_sun_id: SunId, count: int) -> None: ...

class UpgradeSun:
    sun_id: SunId
    def __init__(self, sun_id: SunId) -> None: ...

class SunView:
    id: SunId
    position: Position
    owner: PlayerId
    level: int
    garrison: int
    def __init__(
        self, id: SunId, position: Position, owner: PlayerId, level: int, garrison: int
    ) -> None: ...

class UnitGroupView:
    owner: PlayerId
    count: int
    position: Position
    target_sun_id: SunId
    def __init__(
        self, owner: PlayerId, count: int, position: Position, target_sun_id: SunId
    ) -> None: ...

class GameView:
    my_id: PlayerId
    tick: Tick
    suns: tuple[SunView, ...]
    unit_groups: tuple[UnitGroupView, ...]
    config: GameConfig
    players: tuple[PlayerId, ...]
    eliminated: frozenset[PlayerId]
    def my_suns(self) -> tuple[SunView, ...]: ...
    def enemy_suns(self) -> tuple[SunView, ...]: ...
    def neutral_suns(self) -> tuple[SunView, ...]: ...
    def sun_by_id(self, sun_id: SunId) -> SunView | None: ...
    def my_unit_groups(self) -> tuple[UnitGroupView, ...]: ...
    def enemy_unit_groups(self) -> tuple[UnitGroupView, ...]: ...
    @staticmethod
    def from_state(state: GameState, player_id: PlayerId, config: GameConfig) -> GameView: ...
