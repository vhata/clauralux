from clauralux.engine.campaign import CAMPAIGN_LEVELS
from clauralux.engine.config import GameConfig

VALID_BOT_NAMES = {"passive", "random", "aggressive", "expander"}


def test_campaign_has_18_levels() -> None:
    assert len(CAMPAIGN_LEVELS) == 18


def test_all_levels_produce_valid_state() -> None:
    for i, level in enumerate(CAMPAIGN_LEVELS):
        base_config = GameConfig()
        config = base_config.replace(**level.config_overrides)
        state = level.map_factory(config)

        # Has at least 2 players.
        assert len(state.players) >= 2, f"Level {i + 1} ({level.name}): too few players"

        # Each player owns at least one sun.
        for pid in state.players:
            owned = [s for s in state.suns.values() if s.owner == pid]
            assert len(owned) >= 1, f"Level {i + 1} ({level.name}): P{pid} has no suns"

        # Has some suns.
        assert len(state.suns) >= 3, f"Level {i + 1} ({level.name}): too few suns"


def test_all_bot_names_are_valid() -> None:
    for i, level in enumerate(CAMPAIGN_LEVELS):
        for _pid, bot_name in level.enemy_bots.items():
            assert bot_name in VALID_BOT_NAMES, (
                f"Level {i + 1} ({level.name}): unknown bot '{bot_name}'"
            )


def test_enemy_bots_match_non_p1_players() -> None:
    for i, level in enumerate(CAMPAIGN_LEVELS):
        base_config = GameConfig()
        config = base_config.replace(**level.config_overrides)
        state = level.map_factory(config)

        # Every non-P1 player should have a bot assigned.
        from clauralux.engine.types import PlayerId

        p1 = PlayerId(1)
        non_p1 = [p for p in state.players if p != p1]
        for pid in non_p1:
            assert pid in level.enemy_bots, (
                f"Level {i + 1} ({level.name}): P{pid} has no bot assigned"
            )


def test_difficulty_progression() -> None:
    """Early levels should use weaker bots than later levels."""
    # First 5 levels should only have passive/random enemies.
    weak_bots = {"passive", "random"}
    for level in CAMPAIGN_LEVELS[:5]:
        for bot_name in level.enemy_bots.values():
            assert bot_name in weak_bots, f"Level '{level.name}' too hard for early campaign"

    # Last 3 levels should include aggressive enemies.
    for level in CAMPAIGN_LEVELS[-3:]:
        bot_names = set(level.enemy_bots.values())
        assert "aggressive" in bot_names, f"Level '{level.name}' should have aggressive enemies"
