from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.noisy import NoisyWrapper
from clauralux.bots.passive import PassiveBot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId
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


class TestNoisyWrapper:
    def test_noisy_wrapper_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {
            p1: NoisyWrapper(AggressiveBot(), drop_prob=0.3, seed=42),
            p2: PassiveBot(),
        }
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1

    def test_zero_drop_prob_passes_all_actions(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        inner = AggressiveBot(attack_interval=100)
        for _ in range(100):
            game.tick()
        view = game.get_view(PlayerId(1))
        inner_actions = inner.decide(view)
        # Reset inner state by creating fresh bots.
        inner2 = AggressiveBot(attack_interval=100)
        wrapper = NoisyWrapper(inner2, drop_prob=0.0, seed=42)
        wrapped_actions = wrapper.decide(view)
        assert len(wrapped_actions) == len(inner_actions)

    def test_full_drop_prob_drops_all_actions(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        inner = AggressiveBot(attack_interval=100)
        wrapper = NoisyWrapper(inner, drop_prob=1.0, seed=42)
        for _ in range(100):
            game.tick()
        view = game.get_view(PlayerId(1))
        actions = wrapper.decide(view)
        assert actions == []

    def test_intent_passes_through(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        inner = AggressiveBot()
        wrapper = NoisyWrapper(inner, drop_prob=0.0, seed=42)
        view = game.get_view(PlayerId(1))
        wrapper.decide(view)
        assert wrapper.intent == inner.intent
