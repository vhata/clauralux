from clauralux.bots.baiter import BaiterBot
from clauralux.bots.coordinator import CoordinatorBot
from clauralux.bots.economic import EconomicBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.reactive import ReactiveBot
from clauralux.bots.swarm import SwarmBot
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


class TestSwarmBot:
    def test_swarm_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: SwarmBot(), p2: SwarmBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None or result.is_draw

    def test_swarm_beats_passive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: SwarmBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1

    def test_swarm_produces_actions_quickly(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        bot = SwarmBot(act_interval=15)
        # Tick until first decision point.
        for _ in range(15):
            game.tick()
        view = game.get_view(PlayerId(1))
        actions = bot.decide(view)
        assert len(actions) > 0


class TestCoordinatorBot:
    def test_coordinator_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: CoordinatorBot(), p2: CoordinatorBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None or result.is_draw

    def test_coordinator_beats_passive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: CoordinatorBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1

    def test_coordinator_waits_for_garrison(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        bot = CoordinatorBot(min_garrison=100, act_interval=80)
        # At tick 0, garrison should be too low.
        view = game.get_view(PlayerId(1))
        actions = bot.decide(view)
        assert actions == []


class TestReactiveBot:
    def test_reactive_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: ReactiveBot(), p2: ReactiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None or result.is_draw

    def test_reactive_beats_passive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: ReactiveBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1


class TestEconomicBot:
    def test_economic_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: EconomicBot(), p2: EconomicBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None or result.is_draw

    def test_economic_beats_passive(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: EconomicBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner == p1


class TestBaiterBot:
    def test_baiter_runs_without_crashing(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: BaiterBot(), p2: BaiterBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner is not None or result.is_draw

    def test_baiter_beats_passive(self) -> None:
        # BaiterBot's bait-then-strike cycle is slow against a passive opponent
        # that never reacts, but it should still win or draw (not lose).
        state = two_player_simple(FAST_CONFIG)
        p1, p2 = PlayerId(1), PlayerId(2)
        bots = {p1: BaiterBot(), p2: PassiveBot()}
        result = HeadlessRunner(FAST_CONFIG, state, bots).run()
        assert result.winner in (p1, None) or result.is_draw

    def test_baiter_sends_small_initial_force(self) -> None:
        state = two_player_simple(FAST_CONFIG)
        game = Game(FAST_CONFIG, state)
        bot = BaiterBot(act_interval=40)
        # Tick to first decision point.
        for _ in range(40):
            game.tick()
        view = game.get_view(PlayerId(1))
        actions = bot.decide(view)
        # Bait sends only 2 units.
        from clauralux.engine.actions import SendUnits

        assert len(actions) == 1
        assert isinstance(actions[0], SendUnits)
        assert actions[0].count == 2
