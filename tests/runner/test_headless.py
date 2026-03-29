from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.passive import PassiveBot
from clauralux.engine.config import GameConfig
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import NEUTRAL, PlayerId
from clauralux.runner.headless import HeadlessRunner

FAST_CONFIG = GameConfig(
    map_width=200.0,
    map_height=200.0,
    unit_speed=5.0,
    production_interval=10,
    max_ticks=10000,
    default_neutral_garrison=5.0,
    default_player_garrison=5.0,
)


def test_headless_runner_completes_game() -> None:
    state = two_player_simple(FAST_CONFIG)
    p1, p2 = PlayerId(1), PlayerId(2)
    bots = {p1: AggressiveBot(), p2: PassiveBot()}
    result = HeadlessRunner(FAST_CONFIG, state, bots).run()
    assert result.winner is not None
    assert result.ticks > 0
    assert not result.is_draw


def test_headless_runner_draws_on_timeout() -> None:
    config = GameConfig(max_ticks=100)
    state = two_player_simple(config)
    p1, p2 = PlayerId(1), PlayerId(2)
    bots = {p1: PassiveBot(), p2: PassiveBot()}
    result = HeadlessRunner(config, state, bots).run()
    assert result.is_draw
    assert result.winner == NEUTRAL
