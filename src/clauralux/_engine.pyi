"""Type stubs for the Rust engine extension module."""

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
