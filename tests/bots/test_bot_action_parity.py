"""Action-level parity tests: Python bots vs Rust bots.

Runs the same game state through both implementations and verifies
they produce identical actions on every decision tick. This catches
any divergence between the Python and Rust bot logic.
"""

from __future__ import annotations

from typing import Any

from clauralux._engine import GameConfig, get_rust_bot_actions
from clauralux.bots.registry import BOT_REGISTRY
from clauralux.engine.actions import SendUnits, UpgradeSun
from clauralux.engine.game import Game
from clauralux.engine.maps import two_player_simple
from clauralux.engine.types import PlayerId

_TEST_BOTS = [
    "aggressive",
    "expander",
    "turtle",
    "rush",
    "sniper",
    "opportunist",
    "swarm",
    "coordinator",
    "reactive",
    "economic",
    "baiter",
]


def _extract_state(game: Game, py: Any) -> dict[str, Any]:
    """Extract full game state as arrays for the Rust function."""
    state = game.state
    sun_ids, sun_xs, sun_ys, sun_owners = [], [], [], []
    sun_garrisons, sun_levels, sun_pticks = [], [], []
    for sid, sun in state.suns.items():
        sun_ids.append(int(sid))
        sun_xs.append(float(sun.position.x))
        sun_ys.append(float(sun.position.y))
        sun_owners.append(int(sun.owner))
        sun_garrisons.append(float(sun.garrison))
        sun_levels.append(int(sun.level))
        sun_pticks.append(int(sun.production_ticks))

    g_owners, g_counts, g_xs, g_ys, g_targets = [], [], [], [], []
    for g in state.unit_groups:
        g_owners.append(int(g.owner))
        g_counts.append(int(g.count))
        g_xs.append(float(g.position.x))
        g_ys.append(float(g.position.y))
        g_targets.append(int(g.target_sun_id))

    eliminated = [int(p) for p in state.eliminated]

    return {
        "sun_ids": sun_ids,
        "sun_xs": sun_xs,
        "sun_ys": sun_ys,
        "sun_owners": sun_owners,
        "sun_garrisons": sun_garrisons,
        "sun_levels": sun_levels,
        "sun_production_ticks": sun_pticks,
        "group_owners": g_owners,
        "group_counts": g_counts,
        "group_xs": g_xs,
        "group_ys": g_ys,
        "group_targets": g_targets,
        "players": [1, 2],
        "tick": int(state.tick),
        "eliminated": eliminated,
    }


def _python_actions_to_tuples(actions: list[Any]) -> list[tuple[int, int, int, int]]:
    """Convert Python action objects to the same tuple format as Rust."""
    result = []
    for a in actions:
        if isinstance(a, SendUnits):
            result.append((0, int(a.source_sun_id), int(a.target_sun_id), int(a.count)))
        elif isinstance(a, UpgradeSun):
            result.append((1, int(a.sun_id), 0, 0))
    return result


class TestActionParity:
    """Verify Python and Rust bots produce identical actions on the same state."""

    def test_all_bots_same_actions_on_initial_state(self) -> None:
        """On the starting game state, both implementations must agree."""
        config = GameConfig(max_ticks=10_000)

        for bot_name in _TEST_BOTS:
            state = two_player_simple(config)
            game = Game(config, state)
            bot = BOT_REGISTRY[bot_name]()
            pid = PlayerId(2)

            # Get Python actions.
            view = game.get_view(pid)
            py_actions = _python_actions_to_tuples(bot.decide(view))

            # Get Rust actions.
            s = _extract_state(game, None)
            rs_actions = get_rust_bot_actions(
                config, **s, bot_name=bot_name, player_id=int(pid), rng_seed=42
            )

            assert py_actions == rs_actions, (
                f"{bot_name} tick 0: Python={py_actions}, Rust={rs_actions}"
            )

    def test_all_bots_same_actions_mid_game(self) -> None:
        """After 500 ticks of play, both implementations must still agree."""
        config = GameConfig(max_ticks=10_000)

        for bot_name in _TEST_BOTS:
            state = two_player_simple(config)
            game = Game(config, state)
            p1, p2 = PlayerId(1), PlayerId(2)

            # Use aggressive as P1 to create an interesting game state.
            bot1 = BOT_REGISTRY["aggressive"]()
            bot2 = BOT_REGISTRY[bot_name]()

            # Run 500 ticks with Python bots to build up a game state.
            for _ in range(500):
                if game.is_over:
                    break
                if game.state.tick % config.decision_interval == 0:
                    for pid, bot in [(p1, bot1), (p2, bot2)]:
                        if pid not in game.state.eliminated:
                            view = game.get_view(pid)
                            actions = bot.decide(view)
                            game.apply_actions(pid, actions)
                game.tick()

            if game.is_over:
                continue

            # Now compare what P2's bot would do on this state.
            view = game.get_view(p2)
            py_actions = _python_actions_to_tuples(bot2.decide(view))

            s = _extract_state(game, None)
            rs_actions = get_rust_bot_actions(
                config, **s, bot_name=bot_name, player_id=int(p2), rng_seed=42
            )

            assert py_actions == rs_actions, (
                f"{bot_name} tick {game.state.tick}: Python={py_actions}, Rust={rs_actions}"
            )
