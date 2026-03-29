from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.base import Bot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.engine.config import GameConfig
from clauralux.engine.maps import three_player_triangle, two_player_simple
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.runner.headless import GameResult

MapFactory = Callable[[GameConfig], GameState]

BOT_REGISTRY: dict[str, type[Bot]] = {
    "passive": PassiveBot,
    "random": RandomBot,
    "aggressive": AggressiveBot,
    "expander": ExpanderBot,
}

MAP_REGISTRY: dict[str, MapFactory] = {
    "2p": two_player_simple,
    "3p": three_player_triangle,
}


def make_bot(name: str) -> Bot:
    cls = BOT_REGISTRY.get(name)
    if cls is None:
        print(f"Unknown bot: {name}. Available: {', '.join(BOT_REGISTRY)}")
        sys.exit(1)
    return cls()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clauralux — an Auralux clone")
    parser.add_argument(
        "command",
        choices=["watch", "headless", "tournament"],
        help="watch: visual game, headless: fast bot-vs-bot, tournament: many games",
    )
    parser.add_argument(
        "--bot",
        action="append",
        default=[],
        help=f"Bot type (can repeat). Available: {', '.join(BOT_REGISTRY)}",
    )
    parser.add_argument(
        "--map",
        default="2p",
        choices=list(MAP_REGISTRY),
        help="Map layout (default: 2p)",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=100,
        help="Number of games for tournament mode (default: 100)",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=30000,
        help="Max ticks before draw (default: 30000)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=2.0,
        help="Unit speed (default: 2.0)",
    )

    args = parser.parse_args()

    # Default bots if none specified.
    bot_names: list[str] = args.bot
    map_name: str = args.map

    if map_name == "3p":
        if not bot_names:
            bot_names = ["aggressive", "expander", "random"]
        if len(bot_names) != 3:
            print("3-player map requires exactly 3 bots")
            sys.exit(1)
    else:
        if not bot_names:
            bot_names = ["aggressive", "expander"]
        if len(bot_names) != 2:
            print("2-player map requires exactly 2 bots")
            sys.exit(1)

    config = GameConfig(
        max_ticks=args.max_ticks,
        unit_speed=args.speed,
    )

    if args.command == "watch":
        _run_visual(config, map_name, bot_names)
    elif args.command == "headless":
        _run_headless(config, map_name, bot_names)
    elif args.command == "tournament":
        _run_tournament(config, map_name, bot_names, args.games)


def _make_state_and_bots(
    config: GameConfig, map_name: str, bot_names: list[str]
) -> tuple[GameState, dict[PlayerId, Bot]]:
    map_factory = MAP_REGISTRY[map_name]
    state: GameState = map_factory(config)
    bots: dict[PlayerId, Bot] = {}
    for i, name in enumerate(bot_names):
        bots[PlayerId(i + 1)] = make_bot(name)
    return state, bots


def _run_visual(config: GameConfig, map_name: str, bot_names: list[str]) -> None:
    from clauralux.runner.visual import VisualRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names)
    print(f"Watching: {' vs '.join(bot_names)} on {map_name}")
    print("Controls: Space=pause, Up/Down=speed, Q=quit")
    runner = VisualRunner(config, state, bots)
    result = runner.run()
    _print_result(result, bot_names)


def _run_headless(config: GameConfig, map_name: str, bot_names: list[str]) -> None:
    from clauralux.runner.headless import HeadlessRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names)
    print(f"Running: {' vs '.join(bot_names)} on {map_name}")
    runner = HeadlessRunner(config, state, bots)
    result = runner.run()
    _print_result(result, bot_names)


def _run_tournament(
    config: GameConfig, map_name: str, bot_names: list[str], num_games: int
) -> None:
    from clauralux.runner.tournament import run_tournament

    map_factory = MAP_REGISTRY[map_name]

    bot_factories: dict[PlayerId, Callable[[PlayerId], Bot]] = {}
    for i, name in enumerate(bot_names):
        bot_name = name  # capture for lambda
        bot_factories[PlayerId(i + 1)] = lambda _pid, bn=bot_name: make_bot(bn)  # type: ignore[misc]

    print(f"Tournament: {' vs '.join(bot_names)} on {map_name}, {num_games} games")
    result = run_tournament(
        config=config,
        map_factory=map_factory,
        bot_factories=bot_factories,
        num_games=num_games,
    )

    print(f"\nResults ({result.total_games} games):")
    for i, name in enumerate(bot_names):
        pid = PlayerId(i + 1)
        wins = result.wins.get(pid, 0)
        rate = result.win_rate(pid)
        print(f"  P{pid} ({name}): {wins} wins ({rate:.1%})")
    print(f"  Draws: {result.draws}")
    print(f"  Avg ticks: {result.avg_ticks:.0f}")


def _print_result(result: GameResult, bot_names: list[str]) -> None:
    if result.is_draw:
        print(f"Draw after {result.ticks} ticks")
    else:
        winner_idx = int(result.winner) - 1 if result.winner is not None else -1
        if 0 <= winner_idx < len(bot_names):
            print(f"P{result.winner} ({bot_names[winner_idx]}) wins in {result.ticks} ticks")
        else:
            print(f"P{result.winner} wins in {result.ticks} ticks")
