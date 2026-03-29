from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Callable

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.base import Bot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.engine.campaign import CAMPAIGN_LEVELS
from clauralux.engine.config import GameConfig
from clauralux.engine.mapgen import FLAVOURS, flavour_config, generate_map
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

FLAVOUR_NAMES = list(FLAVOURS.keys())


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
        choices=["watch", "headless", "tournament", "campaign"],
        help="watch/headless/tournament: bot games. campaign: play through levels.",
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
        help=f"Map: {', '.join(MAP_REGISTRY)} or random:FLAVOUR ({', '.join(FLAVOUR_NAMES)})",
    )
    parser.add_argument(
        "--players",
        type=int,
        default=None,
        help="Number of players for random maps (default: inferred from --bot count)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for map generation",
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
    parser.add_argument(
        "--level",
        type=int,
        default=1,
        help="Campaign starting level (default: 1)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run campaign in headless mode",
    )

    args = parser.parse_args()

    if args.command == "campaign":
        _run_campaign(args)
        return

    config = GameConfig(max_ticks=args.max_ticks, unit_speed=args.speed)
    bot_names: list[str] = args.bot
    map_name: str = args.map

    # Resolve map and bot defaults.
    if map_name.startswith("random:"):
        flavour = map_name.split(":", 1)[1]
        if flavour not in FLAVOURS:
            print(f"Unknown flavour: {flavour}. Available: {', '.join(FLAVOUR_NAMES)}")
            sys.exit(1)
        config = flavour_config(config, flavour)
        num_players = args.players or len(bot_names) or 2
        if not bot_names:
            bot_names = ["aggressive", "expander"][:num_players]
            if num_players == 3:
                bot_names = ["aggressive", "expander", "random"]
        if len(bot_names) != num_players:
            print(f"Need {num_players} bots for {num_players}-player map, got {len(bot_names)}")
            sys.exit(1)
    elif map_name == "3p":
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

    if args.command == "watch":
        _run_visual(config, map_name, bot_names, args.seed)
    elif args.command == "headless":
        _run_headless(config, map_name, bot_names, args.seed)
    elif args.command == "tournament":
        _run_tournament(config, map_name, bot_names, args.games, args.seed)


def _resolve_map(
    config: GameConfig, map_name: str, bot_names: list[str], seed: int | None
) -> GameState:
    if map_name.startswith("random:"):
        flavour = map_name.split(":", 1)[1]
        return generate_map(config, flavour, len(bot_names), seed=seed)
    factory = MAP_REGISTRY[map_name]
    return factory(config)


def _make_state_and_bots(
    config: GameConfig, map_name: str, bot_names: list[str], seed: int | None
) -> tuple[GameState, dict[PlayerId, Bot]]:
    state = _resolve_map(config, map_name, bot_names, seed)
    bots: dict[PlayerId, Bot] = {}
    for i, name in enumerate(bot_names):
        bots[PlayerId(i + 1)] = make_bot(name)
    return state, bots


def _run_visual(config: GameConfig, map_name: str, bot_names: list[str], seed: int | None) -> None:
    from clauralux.runner.visual import VisualRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names, seed)
    print(f"Watching: {' vs '.join(bot_names)} on {map_name}")
    print("Controls: Space=pause, Up/Down=speed, Q=quit")
    runner = VisualRunner(config, state, bots)
    result = runner.run()
    _print_result(result, bot_names)


def _run_headless(
    config: GameConfig, map_name: str, bot_names: list[str], seed: int | None
) -> None:
    from clauralux.runner.headless import HeadlessRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names, seed)
    print(f"Running: {' vs '.join(bot_names)} on {map_name}")
    runner = HeadlessRunner(config, state, bots)
    result = runner.run()
    _print_result(result, bot_names)


def _run_tournament(
    config: GameConfig,
    map_name: str,
    bot_names: list[str],
    num_games: int,
    seed: int | None,
) -> None:
    from clauralux.runner.tournament import run_tournament

    def map_factory(cfg: GameConfig) -> GameState:
        return _resolve_map(cfg, map_name, bot_names, seed)

    bot_factories: dict[PlayerId, Callable[[PlayerId], Bot]] = {}
    for i, name in enumerate(bot_names):
        bot_name = name
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


def _run_campaign(args: argparse.Namespace) -> None:
    from clauralux.runner.visual import VisualRunner

    start = max(1, min(args.level, len(CAMPAIGN_LEVELS)))
    p1_bot_name = args.bot[0] if args.bot else "expander"

    print(f"Campaign: P1 = {p1_bot_name}, starting at level {start}")
    print(f"{'─' * 50}")

    for i, level in enumerate(CAMPAIGN_LEVELS[start - 1 :], start=start):
        base_config = GameConfig(max_ticks=args.max_ticks, unit_speed=args.speed)
        config = dataclasses.replace(base_config, **level.config_overrides)
        state = level.map_factory(config)

        # Build bots: P1 is the user's choice, rest from level definition.
        bots: dict[PlayerId, Bot] = {PlayerId(1): make_bot(p1_bot_name)}
        for pid, bot_name in level.enemy_bots.items():
            bots[pid] = make_bot(bot_name)

        enemies = ", ".join(f"P{pid}={name}" for pid, name in level.enemy_bots.items())
        print(f"\nLevel {i}: {level.name}")
        print(f"  {level.description}")
        print(f"  Enemies: {enemies}")

        if args.headless:
            from clauralux.runner.headless import HeadlessRunner

            result = HeadlessRunner(config, state, bots).run()
        else:
            print("  Controls: Space=pause, Up/Down=speed, Q=quit")
            result = VisualRunner(config, state, bots).run()

        bot_names = [p1_bot_name, *level.enemy_bots.values()]
        _print_result(result, bot_names)

        if result.winner == PlayerId(1):
            print("  >>> VICTORY! <<<")
        elif result.is_draw:
            print("  >>> DRAW <<<")
        else:
            print("  >>> DEFEAT <<<")
            break

    else:
        print(f"\n{'─' * 50}")
        print("CAMPAIGN COMPLETE!")


def _print_result(result: GameResult, bot_names: list[str]) -> None:
    if result.is_draw:
        print(f"  Draw after {result.ticks} ticks")
    else:
        winner_idx = int(result.winner) - 1 if result.winner is not None else -1
        if 0 <= winner_idx < len(bot_names):
            print(f"  P{result.winner} ({bot_names[winner_idx]}) wins in {result.ticks} ticks")
        else:
            print(f"  P{result.winner} wins in {result.ticks} ticks")
