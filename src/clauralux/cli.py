from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Callable

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.base import Bot
from clauralux.bots.evolved import EvolvedBot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.opportunist import OpportunistBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.bots.rush import RushBot
from clauralux.bots.sniper import SniperBot
from clauralux.bots.turtle import TurtleBot
from clauralux.engine.campaign import CAMPAIGN_LEVELS
from clauralux.engine.config import CONFIG_FIELD_META, GameConfig
from clauralux.engine.mapgen import FLAVOURS, flavour_config, generate_map
from clauralux.engine.maps import (
    five_player_pentagon,
    four_player_cross,
    six_player_hex,
    three_player_triangle,
    two_player_simple,
)
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.renderer.menu import MenuOption
from clauralux.runner.headless import GameResult

MapFactory = Callable[[GameConfig], GameState]

BOT_REGISTRY: dict[str, type[Bot]] = {
    "passive": PassiveBot,
    "random": RandomBot,
    "aggressive": AggressiveBot,
    "expander": ExpanderBot,
    "turtle": TurtleBot,
    "rush": RushBot,
    "sniper": SniperBot,
    "opportunist": OpportunistBot,
    "evolved": EvolvedBot,
}

MAP_REGISTRY: dict[str, MapFactory] = {
    "2p": two_player_simple,
    "3p": three_player_triangle,
    "4p": four_player_cross,
    "5p": five_player_pentagon,
    "6p": six_player_hex,
}

# Player count for each map. Random maps derive from --players or bot count.
MAP_PLAYER_COUNTS: dict[str, int] = {
    "2p": 2,
    "3p": 3,
    "4p": 4,
    "5p": 5,
    "6p": 6,
}

FLAVOUR_NAMES = list(FLAVOURS.keys())


def _parse_num(s: str, default: float) -> float:
    """Extract the leading number from a string like '30 (default)'."""
    token = s.split()[0] if s else ""
    try:
        return float(token)
    except ValueError:
        return default


def _build_config_from_menu(result: dict[str, str]) -> GameConfig:
    """Build a GameConfig from menu result values, driven by CONFIG_FIELD_META."""
    import dataclasses as dc

    defaults = GameConfig()
    overrides: dict[str, object] = {}

    for field_name in CONFIG_FIELD_META:
        menu_key = f"cfg_{field_name}"
        raw = result.get(menu_key)
        if raw is None:
            continue

        # Get the default value to determine the target type.
        default_val = getattr(defaults, field_name)

        # Special handling for fields that can be None.
        if (default_val is None or isinstance(default_val, int | None)) and (
            "keep" in raw or "no limit" in raw.lower()
        ):
            overrides[field_name] = None
            continue

        num = _parse_num(raw, float("nan"))
        if num != num:  # NaN check — couldn't parse
            continue

        if isinstance(default_val, int):
            overrides[field_name] = int(num)
        elif isinstance(default_val, float):
            overrides[field_name] = float(num)
        elif default_val is None:
            # int | None fields (like max_ticks, capture_level_reset)
            overrides[field_name] = int(num) if num > 0 else None
        else:
            overrides[field_name] = num

    # Handle max_sun_level → upgrade_costs extension.
    max_level = overrides.get("max_sun_level", defaults.max_sun_level)
    if isinstance(max_level, int) and max_level > len(defaults.upgrade_costs) + 1:
        base = defaults.upgrade_costs
        extra = tuple(40 + 20 * i for i in range(max_level - len(base) - 1))
        overrides["upgrade_costs"] = (*base, *extra)

    return dc.replace(defaults, **overrides)  # type: ignore[arg-type]


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
        nargs="?",
        default=None,
        choices=["watch", "headless", "tournament", "campaign", "train"],
        help="watch/headless/tournament/campaign/train. Omit for GUI menu.",
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

    # Training arguments.
    parser.add_argument(
        "--population",
        type=int,
        default=50,
        help="Population size for training (default: 50)",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=100,
        help="Number of generations for training (default: 100)",
    )
    parser.add_argument(
        "--games-per-eval",
        type=int,
        default=20,
        help="Games per fitness evaluation (default: 20)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel workers for training (default: 4)",
    )
    parser.add_argument(
        "--output",
        default="data/evolved_weights.json",
        help="Output path for trained weights (default: data/evolved_weights.json)",
    )

    args = parser.parse_args()

    # No command given — launch GUI menu.
    if args.command is None:
        _run_gui_menu()
        return

    if args.command == "campaign":
        _run_campaign(args)
        return

    if args.command == "train":
        _run_train(args)
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


def _get_player_count_for_map(map_value: str) -> int:
    """Derive player count from a map selection."""
    if map_value in MAP_PLAYER_COUNTS:
        return MAP_PLAYER_COUNTS[map_value]
    # Random maps: look at the "players" option, default to 2.
    return 2


def _build_menu_options() -> list[MenuOption]:
    """Build menu options dynamically from registries."""
    from clauralux.renderer.menu import PLAYER_COLOUR_NAMES

    bot_names = list(BOT_REGISTRY.keys())
    map_choices = list(MAP_REGISTRY.keys()) + [f"random:{f}" for f in FLAVOURS]
    player_count_choices = ["2", "3", "4", "5", "6"]
    campaign_levels = [f"{i + 1}. {lvl.name}" for i, lvl in enumerate(CAMPAIGN_LEVELS)]

    # Default bot assignments: cycle through available bots.
    default_bots = ["expander", "aggressive", "random", "passive", "expander", "aggressive"]

    options: list[MenuOption] = [
        MenuOption(
            key="mode",
            label="Mode",
            description="Watch: visual game. Campaign: play levels. Headless: fast.",
            choices=["watch", "campaign", "headless", "tournament"],
            default_index=0,
        ),
        MenuOption(
            key="map",
            label="Map",
            description="Map layout. 'random:X' generates a themed random map.",
            choices=map_choices,
            default_index=0,
        ),
        MenuOption(
            key="players",
            label="Players (random)",
            description="Number of players for random maps. Ignored for fixed maps.",
            choices=player_count_choices,
            default_index=0,
            visible_when=lambda v: v["map"].startswith("random:"),
        ),
    ]

    # Bot selectors for up to 6 players.
    for i in range(6):
        player_num = i + 1
        colour = PLAYER_COLOUR_NAMES.get(player_num, f"P{player_num}")
        default_idx = bot_names.index(default_bots[i]) if default_bots[i] in bot_names else 0

        def make_visible(n: int) -> Callable[[dict[str, str]], bool]:
            def check(v: dict[str, str]) -> bool:
                if v["mode"] == "campaign":
                    return n == 1  # campaign only needs P1
                map_val = v["map"]
                if map_val in MAP_PLAYER_COUNTS:
                    return n <= MAP_PLAYER_COUNTS[map_val]
                # Random map: use the players option.
                return n <= int(v.get("players", "2"))

            return check

        options.append(
            MenuOption(
                key=f"bot{player_num}",
                label=f"Player {player_num} ({colour})",
                description=f"Bot strategy for Player {player_num} ({colour}).",
                choices=bot_names,
                default_index=default_idx,
                visible_when=make_visible(player_num),
            )
        )

    # Auto-generate config options from CONFIG_FIELD_META.
    def not_campaign(v: dict[str, str]) -> bool:
        return v["mode"] != "campaign"

    for field_name, meta in CONFIG_FIELD_META.items():
        if not meta.menu_visible:
            continue
        options.append(
            MenuOption(
                key=f"cfg_{field_name}",
                label=meta.label,
                description=meta.description,
                choices=list(meta.choices),
                default_index=meta.default_choice,
                visible_when=not_campaign,
            )
        )

    options.extend(
        [
            MenuOption(
                key="campaign_start",
                label="Campaign Start",
                description="Which campaign level to start from.",
                choices=campaign_levels,
                default_index=0,
                visible_when=lambda v: v["mode"] == "campaign",
            ),
        ]
    )

    return options


def _run_gui_menu() -> None:
    """Show the GUI menu and launch the selected game."""
    from clauralux.renderer.menu import MenuScreen

    options = _build_menu_options()
    menu = MenuScreen(options)
    result = menu.run()

    if result is None:
        return  # user quit

    mode = result["mode"]
    map_name = result["map"]

    # Determine player count and collect bot names.
    if map_name in MAP_PLAYER_COUNTS:
        num_players = MAP_PLAYER_COUNTS[map_name]
    elif map_name.startswith("random:"):
        num_players = int(result.get("players", "2"))
    else:
        num_players = 2

    bot_names = [result[f"bot{i + 1}"] for i in range(num_players)]

    # Build GameConfig from menu values using metadata.
    config = _build_config_from_menu(result)
    if map_name.startswith("random:"):
        flavour = map_name.split(":", 1)[1]
        config = flavour_config(config, flavour)

    if mode == "campaign":
        import argparse

        campaign_start_str = result.get("campaign_start", "1. First Light")
        campaign_start = int(campaign_start_str.split(".")[0])
        fake_args = argparse.Namespace(
            bot=[bot_names[0]],
            max_ticks=config.max_ticks or 30000,
            speed=config.unit_speed,
            level=campaign_start,
            headless=False,
        )
        _run_campaign(fake_args)
    elif mode == "watch":
        _run_visual(config, map_name, bot_names, None)
    elif mode == "headless":
        _run_headless(config, map_name, bot_names, None)
    elif mode == "tournament":
        _run_tournament(config, map_name, bot_names, 100, None)


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


def _run_train(args: argparse.Namespace) -> None:
    from clauralux.training.trainer import TrainingConfig, train

    config = TrainingConfig(
        population_size=args.population,
        generations=args.generations,
        games_per_eval=args.games_per_eval,
        workers=args.workers,
        output_path=args.output,
    )
    train(config)


def _print_result(result: GameResult, bot_names: list[str]) -> None:
    if result.is_draw:
        print(f"  Draw after {result.ticks} ticks")
    else:
        winner_idx = int(result.winner) - 1 if result.winner is not None else -1
        if 0 <= winner_idx < len(bot_names):
            print(f"  P{result.winner} ({bot_names[winner_idx]}) wins in {result.ticks} ticks")
        else:
            print(f"  P{result.winner} wins in {result.ticks} ticks")
