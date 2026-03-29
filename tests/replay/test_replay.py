from pathlib import Path

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.expander import ExpanderBot
from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.config import GameConfig
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId, SunId
from clauralux.replay.recorder import (
    GameRecorder,
    load_replay,
    replay_to_game,
    save_replay,
)
from clauralux.replay.replay_bot import ReplayBot
from clauralux.runner.headless import HeadlessRunner

FAST_CONFIG = GameConfig(
    map_width=200.0,
    map_height=200.0,
    unit_speed=5.0,
    production_interval=10,
    max_ticks=5000,
    default_neutral_garrison=5.0,
    default_player_garrison=5.0,
)


class TestGameRecorder:
    def test_records_actions(self) -> None:
        config = GameConfig()
        state = two_player_simple(config)
        recorder = GameRecorder(config, state)
        recorder.record_actions(0, PlayerId(1), [SendUnits(SunId(0), SunId(2), 5)])
        recorder.record_actions(0, PlayerId(2), [UpgradeSun(SunId(1))])
        replay = recorder.finish(winner=PlayerId(1), ticks=100, is_draw=False)
        assert len(replay.actions) == 2
        assert replay.result["winner"] == 1
        assert replay.result["ticks"] == 100

    def test_skips_empty_actions(self) -> None:
        config = GameConfig()
        state = two_player_simple(config)
        recorder = GameRecorder(config, state)
        recorder.record_actions(0, PlayerId(1), [])
        replay = recorder.finish(winner=None, ticks=0, is_draw=True)
        assert len(replay.actions) == 0


class TestSaveLoad:
    def test_roundtrip(self, tmp_path: Path) -> None:
        config = GameConfig(unit_speed=3.0, production_interval=20)
        state = two_player_simple(config)
        recorder = GameRecorder(
            config, state, bot_names={PlayerId(1): "aggressive", PlayerId(2): "expander"}
        )
        recorder.record_actions(0, PlayerId(1), [SendUnits(SunId(0), SunId(2), 5)])
        recorder.record_actions(30, PlayerId(2), [UpgradeSun(SunId(1))])
        replay = recorder.finish(winner=PlayerId(1), ticks=500, is_draw=False)

        path = tmp_path / "test_replay.json"
        save_replay(replay, path)
        loaded = load_replay(path)

        assert loaded.version == 1
        assert loaded.config["unit_speed"] == 3.0
        assert loaded.bot_names == {"1": "aggressive", "2": "expander"}
        assert len(loaded.actions) == 2
        assert loaded.result["winner"] == 1


class TestReplayToGame:
    def test_reconstructs_game(self, tmp_path: Path) -> None:
        config = GameConfig()
        state = two_player_simple(config)
        recorder = GameRecorder(config, state)
        recorder.record_actions(0, PlayerId(1), [SendUnits(SunId(0), SunId(2), 3)])
        replay = recorder.finish(winner=PlayerId(1), ticks=100, is_draw=False)

        path = tmp_path / "test.json"
        save_replay(replay, path)
        loaded = load_replay(path)

        new_config, new_state, schedule = replay_to_game(loaded)
        assert new_config.max_ticks == config.max_ticks
        assert len(new_state.suns) == len(state.suns)
        assert 1 in schedule
        assert len(schedule[1]) == 1
        tick, actions = schedule[1][0]
        assert tick == 0
        assert len(actions) == 1
        assert isinstance(actions[0], SendUnits)


class TestReplayBot:
    def test_replays_actions_at_correct_tick(self) -> None:
        actions_at_0: list[Action] = [SendUnits(SunId(0), SunId(2), 5)]
        actions_at_30: list[Action] = [UpgradeSun(SunId(0))]
        schedule: list[tuple[int, list[Action]]] = [(0, actions_at_0), (30, actions_at_30)]
        bot = ReplayBot(schedule, bot_name="test")

        # Create a view at tick 0.
        config = GameConfig()
        state = two_player_simple(config)
        from clauralux.engine.game import Game

        game = Game(config, state)
        view = game.get_view(PlayerId(1))
        result = bot.decide(view)
        assert len(result) == 1
        assert isinstance(result[0], SendUnits)

    def test_returns_empty_on_non_action_tick(self) -> None:
        schedule: list[tuple[int, list[Action]]] = [(100, [SendUnits(SunId(0), SunId(2), 5)])]
        bot = ReplayBot(schedule)

        config = GameConfig()
        state = two_player_simple(config)
        from clauralux.engine.game import Game

        game = Game(config, state)
        view = game.get_view(PlayerId(1))  # tick 0
        result = bot.decide(view)
        assert result == []


class TestFullReplayRoundtrip:
    def test_record_and_replay_produce_same_result(self, tmp_path: Path) -> None:
        """Record a game, save it, load it, replay it, check same outcome."""
        p1, p2 = PlayerId(1), PlayerId(2)
        state = two_player_simple(FAST_CONFIG)
        bot_names = {p1: "aggressive", p2: "expander"}
        recorder = GameRecorder(FAST_CONFIG, state, bot_names)
        bots = {p1: AggressiveBot(), p2: ExpanderBot()}
        runner = HeadlessRunner(FAST_CONFIG, state, bots, recorder=recorder)
        original_result = runner.run()

        replay_data = recorder.finish(
            original_result.winner, original_result.ticks, original_result.is_draw
        )
        path = tmp_path / "roundtrip.json"
        save_replay(replay_data, path)

        # Load and replay.
        loaded = load_replay(path)
        new_config, new_state, schedule = replay_to_game(loaded)
        replay_bots: dict[PlayerId, ReplayBot] = {}
        for pid_str in loaded.bot_names:
            pid = PlayerId(int(pid_str))
            replay_bots[pid] = ReplayBot(schedule.get(int(pid), []))

        replay_runner = HeadlessRunner(new_config, new_state, replay_bots)
        replay_result = replay_runner.run()

        assert replay_result.winner == original_result.winner
        assert replay_result.ticks == original_result.ticks
        assert replay_result.is_draw == original_result.is_draw
