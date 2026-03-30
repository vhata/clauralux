from clauralux.bots.registry import BOT_REGISTRY
from clauralux.engine.campaign import CAMPAIGN_LEVELS
from clauralux.engine.config import GameConfig
from clauralux.engine.types import PlayerId

VALID_BOT_NAMES = set(BOT_REGISTRY.keys()) - {"human"}


def test_campaign_has_24_levels() -> None:
    assert len(CAMPAIGN_LEVELS) == 24


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
        p1 = PlayerId(1)
        non_p1 = [p for p in state.players if p != p1]
        for pid in non_p1:
            assert pid in level.enemy_bots, (
                f"Level {i + 1} ({level.name}): P{pid} has no bot assigned"
            )


def test_difficulty_progression() -> None:
    """Early levels should use weaker bots than later levels."""
    # First 6 levels (Act 1) should only have passive/random enemies.
    weak_bots = {"passive", "random"}
    for level in CAMPAIGN_LEVELS[:6]:
        for bot_name in level.enemy_bots.values():
            assert bot_name in weak_bots, f"Level '{level.name}' too hard for Act 1"

    # Last level should have aggressive enemies (Final Stand).
    final = CAMPAIGN_LEVELS[-1]
    bot_names = set(final.enemy_bots.values())
    assert "aggressive" in bot_names, f"Final level '{final.name}' should have aggressive enemies"
