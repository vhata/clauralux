from clauralux.engine.config import GameConfig
from clauralux.engine.maps import (
    five_player_pentagon,
    four_player_cross,
    six_player_hex,
    three_player_triangle,
    two_player_simple,
)
from clauralux.engine.types import NEUTRAL


def _check_map(config: GameConfig, factory: object, expected_players: int) -> None:
    state = factory(config)  # type: ignore[operator]
    assert len(state.players) == expected_players

    # Each player owns at least one sun.
    for pid in state.players:
        owned = [s for s in state.suns.values() if s.owner == pid]
        assert len(owned) >= 1, f"P{pid} has no suns"

    # Remaining suns are neutral.
    neutrals = [s for s in state.suns.values() if s.owner == NEUTRAL]
    player_suns = len(state.suns) - len(neutrals)
    assert player_suns >= expected_players

    # All suns within bounds.
    for sun in state.suns.values():
        assert 0 <= sun.position.x <= config.map_width
        assert 0 <= sun.position.y <= config.map_height


def test_two_player_simple() -> None:
    _check_map(GameConfig(), two_player_simple, 2)


def test_three_player_triangle() -> None:
    _check_map(GameConfig(), three_player_triangle, 3)


def test_four_player_cross() -> None:
    _check_map(GameConfig(), four_player_cross, 4)


def test_five_player_pentagon() -> None:
    _check_map(GameConfig(), five_player_pentagon, 5)


def test_six_player_hex() -> None:
    _check_map(GameConfig(), six_player_hex, 6)
