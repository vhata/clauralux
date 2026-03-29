from clauralux.engine.actions import SendUnits, UpgradeSun
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState, Sun
from clauralux.engine.types import NEUTRAL, PlayerId, Position, SunId


def _simple_two_player(
    garrison_p1: float = 10.0,
    garrison_p2: float = 10.0,
    neutral_garrison: float = 5.0,
    distance: float = 100.0,
    **config_overrides: object,
) -> tuple[Game, PlayerId, PlayerId]:
    """Helper: two players with one sun each, one neutral between them."""
    p1 = PlayerId(1)
    p2 = PlayerId(2)
    config = GameConfig(**config_overrides)
    suns = {
        SunId(0): Sun(SunId(0), Position(0, 0), owner=p1, garrison=garrison_p1),
        SunId(1): Sun(SunId(1), Position(distance, 0), owner=p2, garrison=garrison_p2),
        SunId(2): Sun(
            SunId(2), Position(distance / 2, 0), owner=NEUTRAL, garrison=neutral_garrison
        ),
    }
    state = GameState(suns=suns, players=[p1, p2])
    return Game(config, state), p1, p2


class TestSendUnits:
    def test_send_units_creates_group(self) -> None:
        game, p1, _p2 = _simple_two_player()
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 5)])
        game.tick()
        assert len(game.state.unit_groups) == 1
        assert game.state.unit_groups[0].owner == p1
        assert game.state.unit_groups[0].count == 5
        assert game.state.suns[SunId(0)].garrison == 5.0

    def test_send_clamped_to_garrison(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=3.0)
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 100)])
        game.tick()
        assert game.state.unit_groups[0].count == 3
        assert game.state.suns[SunId(0)].garrison == 0.0

    def test_send_zero_units_ignored(self) -> None:
        game, p1, _p2 = _simple_two_player()
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 0)])
        game.tick()
        assert len(game.state.unit_groups) == 0

    def test_send_from_unowned_sun_ignored(self) -> None:
        game, _p1, p2 = _simple_two_player()
        game.apply_actions(p2, [SendUnits(SunId(0), SunId(2), 5)])
        game.tick()
        assert len(game.state.unit_groups) == 0

    def test_send_to_self_ignored(self) -> None:
        game, p1, _p2 = _simple_two_player()
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(0), 5)])
        game.tick()
        assert len(game.state.unit_groups) == 0
        assert game.state.suns[SunId(0)].garrison == 10.0

    def test_send_to_nonexistent_sun_ignored(self) -> None:
        game, p1, _p2 = _simple_two_player()
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(99), 5)])
        game.tick()
        assert len(game.state.unit_groups) == 0


class TestUnitMovement:
    def test_units_move_toward_target(self) -> None:
        game, p1, _p2 = _simple_two_player(distance=100.0)
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 5)])
        game.tick()  # spawns group
        pos_after_spawn = game.state.unit_groups[0].position

        game.tick()  # moves group
        pos_after_move = game.state.unit_groups[0].position

        # Should have moved right (positive x direction)
        assert pos_after_move.x > pos_after_spawn.x


class TestCombat:
    def test_capture_neutral_sun(self) -> None:
        game, p1, _p2 = _simple_two_player(
            garrison_p1=20.0, neutral_garrison=5.0, distance=10.0, unit_speed=20.0
        )
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 10)])

        # Tick until arrival
        for _ in range(20):
            game.tick()
            if game.state.suns[SunId(2)].owner == p1:
                break

        assert game.state.suns[SunId(2)].owner == p1
        assert game.state.suns[SunId(2)].garrison == 5.0  # 10 - 5

    def test_capture_resets_level(self) -> None:
        game, p1, _p2 = _simple_two_player(
            garrison_p1=30.0, garrison_p2=5.0, distance=10.0, unit_speed=20.0
        )
        game.state.suns[SunId(1)].level = 3
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 20)])

        for _ in range(20):
            game.tick()
            if game.state.suns[SunId(1)].owner == p1:
                break

        assert game.state.suns[SunId(1)].level == 1

    def test_capture_keeps_level_when_configured(self) -> None:
        game, p1, _p2 = _simple_two_player(
            garrison_p1=30.0,
            garrison_p2=5.0,
            distance=10.0,
            unit_speed=20.0,
            capture_level_reset=None,
        )
        game.state.suns[SunId(1)].level = 3
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 20)])

        for _ in range(20):
            game.tick()
            if game.state.suns[SunId(1)].owner == p1:
                break

        assert game.state.suns[SunId(1)].level == 3

    def test_reinforce_friendly_sun(self) -> None:
        game, p1, _p2 = _simple_two_player(distance=10.0, unit_speed=20.0)
        # p1 owns sun 0 with 10 garrison. Make sun 2 also owned by p1.
        game.state.suns[SunId(2)].owner = p1
        game.state.suns[SunId(2)].garrison = 3.0

        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 5)])

        for _ in range(20):
            game.tick()

        # Sun 2 should have gained the 5 units (plus any production)
        assert game.state.suns[SunId(2)].garrison >= 8.0


class TestAttackRatio:
    def test_defenders_advantage_repels_attack(self) -> None:
        game, _p1, _p2 = _simple_two_player(
            garrison_p1=20.0,
            neutral_garrison=10.0,
            distance=10.0,
            unit_speed=20.0,
            attack_ratio=0.5,
        )
        game.apply_actions(PlayerId(1), [SendUnits(SunId(0), SunId(2), 15)])

        for _ in range(20):
            game.tick()

        # 15 * 0.5 = 7.5 damage, garrison 10 - 7.5 = 2.5 > 0, not captured
        assert game.state.suns[SunId(2)].owner == NEUTRAL
        assert game.state.suns[SunId(2)].garrison == 2.5

    def test_attackers_advantage_captures_easily(self) -> None:
        game, p1, _p2 = _simple_two_player(
            garrison_p1=20.0,
            neutral_garrison=10.0,
            distance=10.0,
            unit_speed=20.0,
            attack_ratio=2.0,
        )
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(2), 8)])

        for _ in range(20):
            game.tick()
            if game.state.suns[SunId(2)].owner == p1:
                break

        # 8 * 2.0 = 16 damage, garrison 10, captured with 6/2.0 = 3 remaining
        assert game.state.suns[SunId(2)].owner == p1
        assert game.state.suns[SunId(2)].garrison == 3.0


class TestUpgrade:
    def test_upgrade_sun(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=25.0)
        game.apply_actions(p1, [UpgradeSun(SunId(0))])
        game.tick()
        assert game.state.suns[SunId(0)].level == 2
        assert game.state.suns[SunId(0)].garrison == 5.0  # 25 - 20

    def test_upgrade_insufficient_garrison(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=10.0)
        game.apply_actions(p1, [UpgradeSun(SunId(0))])
        game.tick()
        assert game.state.suns[SunId(0)].level == 1
        assert game.state.suns[SunId(0)].garrison == 10.0

    def test_upgrade_max_level_ignored(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=100.0)
        game.state.suns[SunId(0)].level = 3
        game.apply_actions(p1, [UpgradeSun(SunId(0))])
        game.tick()
        assert game.state.suns[SunId(0)].level == 3
        assert game.state.suns[SunId(0)].garrison == 100.0

    def test_upgrade_unowned_sun_ignored(self) -> None:
        game, _p1, p2 = _simple_two_player(garrison_p1=100.0)
        game.apply_actions(p2, [UpgradeSun(SunId(0))])
        game.tick()
        assert game.state.suns[SunId(0)].level == 1


class TestProduction:
    def test_owned_suns_produce_units(self) -> None:
        game, _p1, _p2 = _simple_two_player(garrison_p1=0.0)
        initial = game.state.suns[SunId(0)].garrison

        # Tick for one full production interval
        for _ in range(game.config.production_interval):
            game.tick()

        # Should have produced at least 1 unit
        assert game.state.suns[SunId(0)].garrison >= initial + 1

    def test_neutral_suns_dont_produce(self) -> None:
        game, _p1, _p2 = _simple_two_player(neutral_garrison=5.0)
        for _ in range(100):
            game.tick()
        # Neutral sun garrison doesn't grow
        assert game.state.suns[SunId(2)].garrison == 5.0

    def test_higher_level_produces_faster(self) -> None:
        game, _p1, _p2 = _simple_two_player(garrison_p1=0.0, garrison_p2=0.0)
        game.state.suns[SunId(0)].level = 3
        game.state.suns[SunId(1)].level = 1

        for _ in range(game.config.production_interval * 3):
            game.tick()

        # Level 3 sun should have produced 3x as many units
        g0 = game.state.suns[SunId(0)].garrison
        g1 = game.state.suns[SunId(1)].garrison
        assert g0 > g1


class TestWinCondition:
    def test_player_eliminated_when_no_suns_or_groups(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=0.0, garrison_p2=10.0)
        # Remove p1's sun
        game.state.suns[SunId(0)].owner = NEUTRAL
        game.tick()
        assert p1 in game.state.eliminated

    def test_last_player_standing_wins(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=10.0, garrison_p2=0.0)
        game.state.suns[SunId(1)].owner = NEUTRAL
        game.tick()
        assert game.state.winner == p1

    def test_game_draws_on_max_ticks(self) -> None:
        game, _p1, _p2 = _simple_two_player(max_ticks=5)
        for _ in range(10):
            game.tick()
        assert game.state.winner == NEUTRAL

    def test_game_not_over_while_units_in_flight(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=5.0, garrison_p2=10.0, distance=100.0)
        # Send all of p1's units away, then lose the sun
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 5)])
        game.tick()  # group is in flight, sun has 0 garrison
        game.state.suns[SunId(0)].owner = NEUTRAL
        game.tick()
        # p1 should NOT be eliminated — still has units in flight
        assert p1 not in game.state.eliminated

    def test_is_over_prevents_further_ticks(self) -> None:
        game, _p1, _p2 = _simple_two_player()
        game.state.suns[SunId(1)].owner = NEUTRAL
        game.state.suns[SunId(1)].garrison = 0.0
        game.tick()  # p2 eliminated, p1 wins
        assert game.is_over

        tick_before = game.state.tick
        game.tick()
        assert game.state.tick == tick_before  # no further advancement


class TestView:
    def test_view_shows_integer_garrison(self) -> None:
        game, p1, _p2 = _simple_two_player(garrison_p1=5.7)
        view = game.get_view(p1)
        sun = view.sun_by_id(SunId(0))
        assert sun is not None
        assert sun.garrison == 5

    def test_view_helper_methods(self) -> None:
        game, p1, _p2 = _simple_two_player()
        view = game.get_view(p1)
        assert len(view.my_suns()) == 1
        assert len(view.enemy_suns()) == 1
        assert len(view.neutral_suns()) == 1
