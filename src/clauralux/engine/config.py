from __future__ import annotations

from dataclasses import dataclass

from clauralux._engine import GameConfig

__all__ = ["CONFIG_FIELD_META", "ConfigFieldMeta", "GameConfig"]


@dataclass(frozen=True, slots=True)
class ConfigFieldMeta:
    """Metadata for a GameConfig field — used to auto-generate menu options."""

    label: str  # display name in the menu
    description: str  # help text
    choices: list[str]  # available values (first token is the numeric value)
    default_choice: int = 0  # index into choices matching the config default
    menu_visible: bool = True  # whether to show in menu at all


# Metadata for fields that should appear in the menu.
# Fields not listed here won't appear. Add an entry here to expose a new parameter.
CONFIG_FIELD_META: dict[str, ConfigFieldMeta] = {
    "unit_speed": ConfigFieldMeta(
        label="Unit Speed",
        description="How fast units move. Higher = more aggressive games.",
        choices=["1.0", "1.5", "2.0", "3.0", "5.0"],
        default_choice=2,
    ),
    "production_interval": ConfigFieldMeta(
        label="Production",
        description="Ticks between producing a unit. Lower = faster economy.",
        choices=["10 (fast)", "20", "30 (default)", "50 (slow)", "80 (glacial)"],
        default_choice=2,
    ),
    "attack_ratio": ConfigFieldMeta(
        label="Attack Ratio",
        description="Damage per attacker. <1 = defenders advantage, >1 = attackers.",
        choices=["0.5 (defenders)", "0.8", "1.0 (fair)", "1.5", "2.0 (attackers)"],
        default_choice=2,
    ),
    "max_sun_level": ConfigFieldMeta(
        label="Max Sun Level",
        description="Maximum upgrade level for suns.",
        choices=["1 (no upgrades)", "2", "3 (default)", "5"],
        default_choice=2,
    ),
    "capture_level_reset": ConfigFieldMeta(
        label="Capture Reset",
        description="What level a sun resets to when captured.",
        choices=["1 (default)", "keep level"],
        default_choice=0,
    ),
    "max_ticks": ConfigFieldMeta(
        label="Max Ticks",
        description="Game ends in a draw after this many ticks. 0 = no limit.",
        choices=["10000", "30000 (default)", "60000", "0 (no limit)"],
        default_choice=1,
    ),
    "default_neutral_garrison": ConfigFieldMeta(
        label="Neutral Garrison",
        description="Starting garrison for neutral suns.",
        choices=["3 (weak)", "5", "10 (default)", "20 (tough)", "40 (fortress)"],
        default_choice=2,
    ),
    "default_player_garrison": ConfigFieldMeta(
        label="Player Start Garrison",
        description="Starting garrison for each player's home sun.",
        choices=["1", "5 (default)", "10", "20"],
        default_choice=1,
    ),
    "decision_interval": ConfigFieldMeta(
        label="Bot Think Speed",
        description="How often bots make decisions (every N ticks). Higher = slower reactions.",
        choices=["1 (every tick)", "5", "10", "20 (sluggish)"],
        default_choice=0,
    ),
}
