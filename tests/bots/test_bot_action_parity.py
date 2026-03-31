"""Action-level parity tests: Python bots vs Rust bots.

Runs the same game state through both implementations and verifies
they produce identical actions. This isolates the opponent bot logic
from the evolved bot's known FP divergence.
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


def _extract_state(game: Game) -> dict[str, Any]:
    """Extract full game state as arrays for the Rust function."""
    state = game.state
    sun_ids: list[int] = []
    sun_xs: list[float] = []
    sun_ys: list[float] = []
    sun_owners: list[int] = []
    sun_garrisons: list[float] = []
    sun_levels: list[int] = []
    sun_pticks: list[int] = []
    for sid, sun in state.suns.items():
        sun_ids.append(int(sid))
        sun_xs.append(float(sun.position.x))
        sun_ys.append(float(sun.position.y))
        sun_owners.append(int(sun.owner))
        sun_garrisons.append(float(sun.garrison))
        sun_levels.append(int(sun.level))
        sun_pticks.append(int(sun.production_ticks))

    g_owners: list[int] = []
    g_counts: list[int] = []
    g_xs: list[float] = []
    g_ys: list[float] = []
    g_targets: list[int] = []
    for g in state.unit_groups:
        g_owners.append(int(g.owner))
        g_counts.append(int(g.count))
        g_xs.append(float(g.position.x))
        g_ys.append(float(g.position.y))
        g_targets.append(int(g.target_sun_id))

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
        "eliminated": [int(p) for p in state.eliminated],
    }


def _py_actions_to_tuples(actions: list[Any]) -> list[tuple[int, int, int, int]]:
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

    def test_initial_state(self) -> None:
        """On the starting game state, all bots must produce identical actions."""
        config = GameConfig(max_ticks=10_000)

        for bot_name in _TEST_BOTS:
            state = two_player_simple(config)
            game = Game(config, state)
            pid = PlayerId(2)

            py_actions = _py_actions_to_tuples(BOT_REGISTRY[bot_name]().decide(game.get_view(pid)))

            s = _extract_state(game)
            rs_actions = get_rust_bot_actions(
                config, **s, bot_name=bot_name, player_id=int(pid), rng_seed=42
            )

            assert py_actions == rs_actions, (
                f"{bot_name} tick 0: Python={py_actions}, Rust={rs_actions}"
            )

    def test_mid_game_state(self) -> None:
        """After 500 ticks of play, all bots must still produce identical actions."""
        config = GameConfig(max_ticks=10_000)

        for bot_name in _TEST_BOTS:
            state = two_player_simple(config)
            game = Game(config, state)
            p1, p2 = PlayerId(1), PlayerId(2)

            bot1 = BOT_REGISTRY["aggressive"]()
            bot2 = BOT_REGISTRY[bot_name]()

            for _ in range(500):
                if game.is_over:
                    break
                if game.state.tick % config.decision_interval == 0:
                    for pid, bot in [(p1, bot1), (p2, bot2)]:
                        if pid not in game.state.eliminated:
                            actions = bot.decide(game.get_view(pid))
                            game.apply_actions(pid, actions)
                game.tick()

            if game.is_over:
                continue

            # Compare P2's decision on this exact state.
            py_actions = _py_actions_to_tuples(bot2.decide(game.get_view(p2)))

            s = _extract_state(game)
            rs_actions = get_rust_bot_actions(
                config, **s, bot_name=bot_name, player_id=int(p2), rng_seed=42
            )

            assert py_actions == rs_actions, (
                f"{bot_name} tick {game.state.tick}: Python={py_actions}, Rust={rs_actions}"
            )
