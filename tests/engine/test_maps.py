from clauralux.engine.config import GameConfig
from clauralux.engine.maps import three_player_triangle, two_player_simple
from clauralux.engine.types import NEUTRAL


def test_two_player_simple_has_correct_structure() -> None:
    config = GameConfig()
    state = two_player_simple(config)
    assert len(state.suns) == 5
    assert len(state.players) == 2

    owners = [s.owner for s in state.suns.values()]
    assert owners.count(NEUTRAL) == 3
    non_neutral = [o for o in owners if o != NEUTRAL]
    assert len(non_neutral) == 2
    assert len(set(non_neutral)) == 2  # two different players


def test_three_player_triangle_has_correct_structure() -> None:
    config = GameConfig()
    state = three_player_triangle(config)
    assert len(state.suns) == 7
    assert len(state.players) == 3

    owners = [s.owner for s in state.suns.values()]
    assert owners.count(NEUTRAL) == 4
