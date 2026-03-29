from clauralux.engine.config import GameConfig
from clauralux.engine.maps import two_player_simple
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId
from clauralux.runner.headless import GameResult
from clauralux.training.evolution import _score_game


class TestScoreGame:
    def _make_state(self, config: GameConfig, p1_suns: int, p2_suns: int) -> GameState:
        """Create a simple state with the given sun ownership for scoring."""
        state = two_player_simple(config)
        # Reassign sun ownership based on counts requested.
        suns = state.suns
        sun_ids = sorted(suns.keys())
        for i, sid in enumerate(sun_ids):
            sun = suns[sid]
            if i < p1_suns:
                sun.owner = PlayerId(1)
            elif i < p1_suns + p2_suns:
                sun.owner = PlayerId(2)
            else:
                sun.owner = NEUTRAL
        return state

    def test_win_scores_higher_than_draw(self) -> None:
        config = GameConfig(max_ticks=10000)
        state = self._make_state(config, p1_suns=3, p2_suns=0)

        win_result = GameResult(
            winner=PlayerId(1), ticks=5000, eliminated=frozenset(), is_draw=False
        )
        draw_result = GameResult(winner=NEUTRAL, ticks=5000, eliminated=frozenset(), is_draw=True)

        win_score = _score_game(win_result, state, PlayerId(1), 10000)
        draw_score = _score_game(draw_result, state, PlayerId(1), 10000)
        assert win_score > draw_score

    def test_draw_scores_higher_than_loss(self) -> None:
        config = GameConfig(max_ticks=10000)
        state = self._make_state(config, p1_suns=2, p2_suns=2)

        draw_result = GameResult(winner=NEUTRAL, ticks=5000, eliminated=frozenset(), is_draw=True)
        loss_result = GameResult(
            winner=PlayerId(2), ticks=5000, eliminated=frozenset(), is_draw=False
        )

        draw_score = _score_game(draw_result, state, PlayerId(1), 10000)
        loss_score = _score_game(loss_result, state, PlayerId(1), 10000)
        assert draw_score > loss_score

    def test_fast_win_scores_higher_than_slow_win(self) -> None:
        config = GameConfig(max_ticks=10000)
        state = self._make_state(config, p1_suns=3, p2_suns=0)

        fast_result = GameResult(
            winner=PlayerId(1), ticks=1000, eliminated=frozenset(), is_draw=False
        )
        slow_result = GameResult(
            winner=PlayerId(1), ticks=9000, eliminated=frozenset(), is_draw=False
        )

        fast_score = _score_game(fast_result, state, PlayerId(1), 10000)
        slow_score = _score_game(slow_result, state, PlayerId(1), 10000)
        assert fast_score > slow_score

    def test_more_territory_scores_higher(self) -> None:
        config = GameConfig(max_ticks=10000)
        loss_result = GameResult(
            winner=PlayerId(2), ticks=5000, eliminated=frozenset(), is_draw=False
        )

        state_good = self._make_state(config, p1_suns=3, p2_suns=1)
        state_bad = self._make_state(config, p1_suns=0, p2_suns=4)

        good_score = _score_game(loss_result, state_good, PlayerId(1), 10000)
        bad_score = _score_game(loss_result, state_bad, PlayerId(1), 10000)
        assert good_score > bad_score
