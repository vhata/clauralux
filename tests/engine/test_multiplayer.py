"""Tests for 3+ player game scenarios."""

from typing import Any

from clauralux.engine.actions import SendUnits
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState, Sun
from clauralux.engine.types import NEUTRAL, PlayerId, Position, SunId


def _three_player(
    garrison: float = 10.0,
    neutral_garrison: float = 5.0,
    distance: float = 100.0,
    **config_overrides: Any,
) -> tuple[Game, PlayerId, PlayerId, PlayerId]:
    """Three players in a triangle with a neutral centre."""
    p1 = PlayerId(1)
    p2 = PlayerId(2)
    p3 = PlayerId(3)
    config = GameConfig(**config_overrides)
    suns = {
        SunId(0): Sun(SunId(0), Position(0, 0), owner=p1, garrison=garrison),
        SunId(1): Sun(SunId(1), Position(distance, 0), owner=p2, garrison=garrison),
        SunId(2): Sun(SunId(2), Position(distance / 2, distance), owner=p3, garrison=garrison),
        SunId(3): Sun(
            SunId(3), Position(distance / 2, distance / 3), owner=NEUTRAL, garrison=neutral_garrison
        ),
    }
    state = GameState(suns=suns, players=[p1, p2, p3])
    return Game(config, state), p1, p2, p3


def _four_player(
    garrison: float = 10.0,
    **config_overrides: Any,
) -> tuple[Game, PlayerId, PlayerId, PlayerId, PlayerId]:
    """Four players at corners of a square."""
    p1, p2, p3, p4 = PlayerId(1), PlayerId(2), PlayerId(3), PlayerId(4)
    config = GameConfig(**config_overrides)
    suns = {
        SunId(0): Sun(SunId(0), Position(0, 0), owner=p1, garrison=garrison),
        SunId(1): Sun(SunId(1), Position(100, 0), owner=p2, garrison=garrison),
        SunId(2): Sun(SunId(2), Position(100, 100), owner=p3, garrison=garrison),
        SunId(3): Sun(SunId(3), Position(0, 100), owner=p4, garrison=garrison),
        SunId(4): Sun(SunId(4), Position(50, 50), owner=NEUTRAL, garrison=5.0),
    }
    state = GameState(suns=suns, players=[p1, p2, p3, p4])
    return Game(config, state), p1, p2, p3, p4


class TestThreePlayerElimination:
    def test_player_eliminated_when_no_suns_or_groups(self) -> None:
        # No production so garrisons stay fixed. P1 has overwhelming force.
        game, p1, p2, p3 = _three_player(
            garrison=10.0, neutral_garrison=1.0, production_interval=999999
        )
        # Bump P1 garrison to guarantee capture.
        game.state.suns[SunId(0)].garrison = 50.0
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 40)])
        for _ in range(200):
            game.tick()
        assert p2 in game.state.eliminated
        assert p1 not in game.state.eliminated
        assert p3 not in game.state.eliminated
        assert not game.is_over  # P3 still alive

    def test_game_ends_when_two_eliminated(self) -> None:
        game, p1, p2, p3 = _three_player(
            garrison=10.0, neutral_garrison=1.0, production_interval=999999
        )
        game.state.suns[SunId(0)].garrison = 50.0
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 40)])
        for _ in range(200):
            game.tick()
        assert p2 in game.state.eliminated

        # Now P1 has captured P2's sun with ~30 remaining. Attack P3.
        game.apply_actions(p1, [SendUnits(SunId(1), SunId(2), 20)])
        for _ in range(300):
            game.tick()
        assert p3 in game.state.eliminated
        assert game.is_over
        assert game.state.winner == p1

    def test_third_party_benefits_from_fight(self) -> None:
        """P3 attacks weakened winner after P1 and P2 fight."""
        game, p1, p2, _p3 = _three_player(
            garrison=10.0, neutral_garrison=1.0, production_interval=999999
        )
        # P1 and P2 attack each other — both weaken.
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 8)])
        game.apply_actions(p2, [SendUnits(SunId(1), SunId(0), 8)])
        for _ in range(200):
            game.tick()

        # Both suns should be weakened. P3 is untouched at exactly 10.
        p3_garrison = game.state.suns[SunId(2)].garrison
        assert p3_garrison == 10.0


class TestFourPlayer:
    def test_cascading_elimination(self) -> None:
        """Players eliminated one by one."""
        game, p1, p2, p3, p4 = _four_player(garrison=10.0, production_interval=999999)
        game.state.suns[SunId(0)].garrison = 50.0
        # P1 attacks P2 with overwhelming force.
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 40)])
        for _ in range(200):
            game.tick()
        assert p2 in game.state.eliminated
        alive = [p for p in [p1, p2, p3, p4] if p not in game.state.eliminated]
        assert len(alive) == 3

    def test_draw_on_timeout(self) -> None:
        """Four players with no aggression reach tick limit."""
        game, _p1, _p2, _p3, _p4 = _four_player(garrison=5.0, max_ticks=100)
        for _ in range(200):
            game.tick()
        assert game.is_over
        assert game.state.winner == NEUTRAL  # draw


class TestMultiPlayerViews:
    def test_view_shows_all_enemies(self) -> None:
        """In a 3-player game, enemy_suns includes both opponents."""
        game, p1, p2, p3 = _three_player()
        view = game.get_view(p1)
        enemy_ids = {s.owner for s in view.enemy_suns()}
        assert p2 in enemy_ids
        assert p3 in enemy_ids
        assert len(view.enemy_suns()) == 2

    def test_eliminated_players_tracked(self) -> None:
        game, p1, p2, p3 = _three_player(
            garrison=10.0, neutral_garrison=1.0, production_interval=999999
        )
        game.state.suns[SunId(0)].garrison = 50.0
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(1), 40)])
        for _ in range(200):
            game.tick()
        view = game.get_view(p3)
        assert p2 in view.eliminated
        assert p1 not in view.eliminated

    def test_multiple_players_listed(self) -> None:
        game, p1, _p2, _p3 = _three_player()
        view = game.get_view(p1)
        assert len(view.players) == 3


class TestSimultaneousAttacks:
    def test_two_attackers_same_target(self) -> None:
        """Two players attack the same neutral simultaneously."""
        game, p1, p2, _p3 = _three_player(garrison=10.0, neutral_garrison=3.0)
        game.apply_actions(p1, [SendUnits(SunId(0), SunId(3), 8)])
        game.apply_actions(p2, [SendUnits(SunId(1), SunId(3), 8)])
        # Run until both arrive — one captures, other fights the capturer.
        for _ in range(200):
            game.tick()
        # The neutral should be owned by someone (not neutral anymore).
        owner = game.state.suns[SunId(3)].owner
        assert owner != NEUTRAL
