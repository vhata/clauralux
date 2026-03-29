from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import FLAVOURS, flavour_config, generate_map
from clauralux.engine.types import NEUTRAL


def _check_valid_state(config: GameConfig, flavour: str, num_players: int, seed: int = 42) -> None:
    """Shared validation for generated maps."""
    state = generate_map(config, flavour, num_players, seed=seed)

    # Correct number of players.
    assert len(state.players) == num_players

    # All suns are within map bounds (with some margin tolerance).
    for sun in state.suns.values():
        assert 0 <= sun.position.x <= config.map_width
        assert 0 <= sun.position.y <= config.map_height

    # Each player owns exactly one sun.
    for pid in state.players:
        owned = [s for s in state.suns.values() if s.owner == pid]
        assert len(owned) == 1

    # Remaining suns are neutral.
    neutrals = [s for s in state.suns.values() if s.owner == NEUTRAL]
    assert len(neutrals) == len(state.suns) - num_players


class TestGenerateMap:
    def test_all_flavours_2_players(self) -> None:
        config = GameConfig()
        for flavour in FLAVOURS:
            _check_valid_state(config, flavour, 2)

    def test_all_flavours_3_players(self) -> None:
        config = GameConfig()
        for flavour in FLAVOURS:
            _check_valid_state(config, flavour, 3)

    def test_deterministic_with_same_seed(self) -> None:
        config = GameConfig()
        state1 = generate_map(config, "rush", 2, seed=99)
        state2 = generate_map(config, "rush", 2, seed=99)
        positions1 = [(s.position.x, s.position.y) for s in state1.suns.values()]
        positions2 = [(s.position.x, s.position.y) for s in state2.suns.values()]
        assert positions1 == positions2

    def test_different_seeds_differ(self) -> None:
        config = GameConfig()
        state1 = generate_map(config, "strategic", 2, seed=1)
        state2 = generate_map(config, "strategic", 2, seed=2)
        positions1 = [(s.position.x, s.position.y) for s in state1.suns.values()]
        positions2 = [(s.position.x, s.position.y) for s in state2.suns.values()]
        assert positions1 != positions2

    def test_minimum_spacing_respected(self) -> None:
        config = GameConfig()
        for flavour, params in FLAVOURS.items():
            state = generate_map(config, flavour, 2, seed=42)
            suns = list(state.suns.values())
            for i, a in enumerate(suns):
                for b in suns[i + 1 :]:
                    dist = a.position.distance_to(b.position)
                    # Allow small tolerance for player placement rounding.
                    assert dist >= params.min_sun_spacing * 0.9, (
                        f"{flavour}: suns too close ({dist:.1f} < {params.min_sun_spacing})"
                    )

    def test_sun_count_in_range(self) -> None:
        config = GameConfig()
        for flavour, params in FLAVOURS.items():
            state = generate_map(config, flavour, 2, seed=42)
            assert params.total_suns[0] <= len(state.suns) <= params.total_suns[1]


class TestFlavourConfig:
    def test_applies_overrides(self) -> None:
        base = GameConfig()
        rush_config = flavour_config(base, "rush")
        assert rush_config.production_interval == 15
        assert rush_config.unit_speed == 3.0
        # Other fields stay default.
        assert rush_config.map_width == base.map_width

    def test_unknown_flavour_returns_base(self) -> None:
        base = GameConfig()
        result = flavour_config(base, "nonexistent")
        assert result is base
