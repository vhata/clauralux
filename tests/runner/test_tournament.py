from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.passive import PassiveBot
from clauralux.engine.config import GameConfig
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId
from clauralux.runner.tournament import run_tournament

FAST_CONFIG = GameConfig(
    map_width=200.0,
    map_height=200.0,
    unit_speed=5.0,
    production_interval=10,
    max_ticks=10000,
    default_neutral_garrison=5.0,
    default_player_garrison=5.0,
)


def test_tournament_runs_multiple_games() -> None:
    p1, p2 = PlayerId(1), PlayerId(2)

    result = run_tournament(
        config=FAST_CONFIG,
        map_factory=two_player_simple,
        bot_factories={
            p1: lambda _pid: AggressiveBot(),
            p2: lambda _pid: PassiveBot(),
        },
        num_games=5,
    )

    assert result.total_games == 5
    assert len(result.results) == 5
    assert result.wins.get(p1, 0) > 0
    assert result.win_rate(p1) > 0.0
    assert result.avg_ticks > 0
