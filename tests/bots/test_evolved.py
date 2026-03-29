from clauralux.bots.evolved import EvolvedBot
from clauralux.engine.actions import SendUnits, UpgradeSun
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import HeadlessRunner
from clauralux.training.genome import default_genome

FAST_CONFIG = GameConfig(
    map_width=200.0,
    map_height=200.0,
    unit_speed=5.0,
    production_interval=10,
    max_ticks=10000,
    default_neutral_garrison=5.0,
    default_player_garrison=5.0,
)


class TestEvolvedBot:
    def test_instantiation_with_defaults(self) -> None:
        bot = EvolvedBot()
        assert bot.intent == ""

    def test_instantiation_with_genome(self) -> None:
        g = default_genome()
        bot = EvolvedBot(genome=g)
        assert bot.intent == ""

    def test_decide_returns_valid_actions(self) -> None:
        config = GameConfig()
        state = two_player_simple(config)
        game = Game(config, state)
        bot = EvolvedBot(genome=default_genome())
        # Run a few ticks to build up garrison.
        for _ in range(100):
            game.tick()
        view = game.get_view(PlayerId(1))
        actions = bot.decide(view)
        for action in actions:
            assert isinstance(action, SendUnits | UpgradeSun)

    def test_runs_full_game_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        bots = {
            PlayerId(1): EvolvedBot(genome=default_genome()),
            PlayerId(2): EvolvedBot(genome=default_genome()),
        }
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None

    def test_sets_intent(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        bot = EvolvedBot(genome=default_genome())
        game = Game(FAST_CONFIG, state)
        # Run enough ticks for bot to make a decision.
        for _tick in range(200):
            view = game.get_view(PlayerId(1))
            bot.decide(view)
            game.tick()
        # Intent should have been set at some point.
        assert bot.intent != ""
