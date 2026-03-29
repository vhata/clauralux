from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import HeadlessRunner

# A fast config for tests: small map, fast units, quick production.
FAST_CONFIG = GameConfig(
    map_width=200.0,
    map_height=200.0,
    unit_speed=5.0,
    production_interval=10,
    max_ticks=10000,
    default_neutral_garrison=5.0,
    default_player_garrison=5.0,
)


class TestPassiveBot:
    def test_passive_does_nothing(self) -> None:
        config = GameConfig()
        state = two_player_simple(config)
        p1 = PlayerId(1)
        bot = PassiveBot()
        game = Game(config, state)
        view = game.get_view(p1)
        assert bot.decide(view) == []

    def test_passive_loses_to_aggressive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: AggressiveBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1


class TestRandomBot:
    def test_random_bot_runs_without_crashing(self) -> None:
        config = GameConfig(max_ticks=2000)
        state = two_player_simple(config)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: RandomBot(seed=42), p2: RandomBot(seed=123)}
        result = HeadlessRunner(config, state, bots).run()
        assert result.winner is not None


class TestAggressiveBot:
    def test_aggressive_produces_actions(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        bot = AggressiveBot(attack_interval=100)
        # Tick until enough units accumulate to trigger an attack.
        for _ in range(100):
            game.tick()
        view = game.get_view(PlayerId(1))
        actions = bot.decide(view)
        assert len(actions) > 0


class TestExpanderBot:
    def test_expander_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: ExpanderBot(), p2: ExpanderBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None

    def test_expander_beats_passive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: ExpanderBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1
