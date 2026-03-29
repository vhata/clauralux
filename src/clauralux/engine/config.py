from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameConfig:
    """All tunable game parameters. Nothing is hard-coded elsewhere."""

    # Map dimensions
    map_width: float = 1000.0
    map_height: float = 800.0

    # Sun production: each owned sun produces (level * production_per_level) units
    # every production_interval ticks.
    production_interval: int = 30
    production_per_level: int = 1

    # Sun levels and upgrading
    max_sun_level: int = 3
    # Cost in garrison units to upgrade FROM level N to level N+1.
    # Index 0 = cost from level 1→2, index 1 = cost from level 2→3, etc.
    upgrade_costs: tuple[int, ...] = (20, 40)

    # What level a sun resets to when captured. None = keep current level.
    capture_level_reset: int | None = 1

    # Unit movement
    unit_speed: float = 2.0  # distance per tick

    # Combat: how many defenders one attacker removes.
    # 1.0 = fair fight, >1.0 = attackers advantaged, <1.0 = defenders advantaged.
    attack_ratio: float = 1.0

    # How often bots get polled (every N ticks). 1 = every tick.
    decision_interval: int = 1

    # Game length cap. None = no limit.
    max_ticks: int | None = 30_000

    # Ticks per second for visual mode (ignored in headless).
    ticks_per_second: int = 50

    # Initial garrison for neutral suns (if not set per-sun).
    default_neutral_garrison: float = 10.0

    # Initial garrison for player-owned starting suns.
    default_player_garrison: float = 5.0

    # Random seed for deterministic simulation. None = random.
    seed: int | None = 42
