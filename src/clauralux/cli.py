from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from clauralux.bots.base import Bot
from clauralux.bots.registry import BOT_DESCRIPTIONS, BOT_REGISTRY
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

_CONFIG_DIR = Path.home() / ".config" / "clauralux"
_SETTINGS_PATH = _CONFIG_DIR / "settings.json"


def _load_settings() -> dict[str, str]:
    """Load saved menu settings from disk. Returns empty dict on any error."""
    try:
        return json.loads(_SETTINGS_PATH.read_text())  # type: ignore[no-any-return]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_settings(settings: dict[str, str]) -> None:
    """Save menu settings to disk. Silently ignores errors."""
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
    except OSError:
        pass


def _parse_num(s: str, default: float) -> float:
    """Extract the leading number from a string like '30 (default)'."""
    token = s.split()[0] if s else ""
    try:
        return float(token)
    except ValueError:
        return default


def _build_config_from_menu(result: dict[str, str]) -> GameConfig:
    """Build a GameConfig from menu result values, driven by CONFIG_FIELD_META."""
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

    return defaults.replace(**overrides)


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
        choices=[
            "watch",
            "headless",
            "tournament",
            "campaign",
            "train",
            "megatrain",
            "replay",
            "benchmark",
        ],
        help="Game mode. Omit for GUI menu.",
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
        default=80,
        help="Population size for training (default: 80)",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=200,
        help="Number of generations for training (default: 200)",
    )
    parser.add_argument(
        "--games-per-eval",
        type=int,
        default=40,
        help="Games per fitness evaluation (default: 40)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel workers for training (0 = all CPUs, default: 0)",
    )
    parser.add_argument(
        "--output",
        default="data/evolved_weights.json",
        help="Output path for trained weights (default: data/evolved_weights.json)",
    )
    parser.add_argument(
        "--from-scratch",
        action="store_true",
        help="Train from scratch, ignoring existing weights",
    )
    parser.add_argument(
        "--self-play",
        action="store_true",
        help="Train only against other evolved bots (no hand-crafted opponents)",
    )

    # Benchmark arguments.
    parser.add_argument(
        "--benchmark-games",
        type=int,
        default=50,
        help="Games per opponent for benchmark (default: 50)",
    )

    # Replay arguments.
    parser.add_argument(
        "--record",
        default=None,
        metavar="FILE",
        help="Record the game to a replay JSON file",
    )
    parser.add_argument(
        "replay_file",
        nargs="?",
        default=None,
        help="Replay file to play back (for 'replay' command)",
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

    if args.command == "megatrain":
        _run_megatrain(args)
        return

    if args.command == "benchmark":
        _run_benchmark(args)
        return

    if args.command == "replay":
        _run_replay(args)
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
        _run_visual(config, map_name, bot_names, args.seed, record_path=args.record)
    elif args.command == "headless":
        _run_headless(config, map_name, bot_names, args.seed, record_path=args.record)
    elif args.command == "tournament":
        _run_tournament(config, map_name, bot_names, args.games, args.seed)


def _get_player_count_for_map(map_value: str) -> int:
    """Derive player count from a map selection."""
    if map_value in MAP_PLAYER_COUNTS:
        return MAP_PLAYER_COUNTS[map_value]
    # Random maps: look at the "players" option, default to 2.
    return 2


def _saved_index(choices: list[str], saved_value: str | None, fallback: int) -> int:
    """Find the index of a saved value in a choices list, or return fallback."""
    if saved_value is None:
        return fallback
    try:
        return choices.index(saved_value)
    except ValueError:
        return fallback


def _build_menu_options(saved: dict[str, str] | None = None) -> list[MenuOption]:
    """Build menu options dynamically from registries."""
    from clauralux.renderer.menu import PLAYER_COLOUR_NAMES

    s = saved or {}
    bot_names = list(BOT_REGISTRY.keys())
    map_choices = list(MAP_REGISTRY.keys()) + [f"random:{f}" for f in FLAVOURS]
    player_count_choices = ["2", "3", "4", "5", "6"]
    campaign_levels = [f"{i + 1}. {lvl.name}" for i, lvl in enumerate(CAMPAIGN_LEVELS)]

    # Default bot assignments: cycle through available bots.
    default_bots = ["expander", "aggressive", "random", "passive", "expander", "aggressive"]

    mode_choices = ["watch", "campaign", "headless", "tournament"]
    options: list[MenuOption] = [
        MenuOption(
            key="mode",
            label="Mode",
            description="Watch: visual game. Campaign: play levels. Headless: fast.",
            choices=mode_choices,
            default_index=_saved_index(mode_choices, s.get("mode"), 0),
        ),
        MenuOption(
            key="map",
            label="Map",
            description="Map layout. 'random:X' generates a themed random map.",
            choices=map_choices,
            default_index=_saved_index(map_choices, s.get("map"), 0),
        ),
        MenuOption(
            key="players",
            label="Players (random)",
            description="Number of players for random maps. Ignored for fixed maps.",
            choices=player_count_choices,
            default_index=_saved_index(player_count_choices, s.get("players"), 0),
            visible_when=lambda v: v["map"].startswith("random:"),
        ),
    ]

    # Bot selectors for up to 6 players.
    for i in range(6):
        player_num = i + 1
        colour = PLAYER_COLOUR_NAMES.get(player_num, f"P{player_num}")
        hardcoded_default = bot_names.index(default_bots[i]) if default_bots[i] in bot_names else 0
        default_idx = _saved_index(bot_names, s.get(f"bot{player_num}"), hardcoded_default)

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

        def make_bot_description(bot_name: str) -> str:
            return BOT_DESCRIPTIONS.get(bot_name, f"Bot strategy: {bot_name}")

        options.append(
            MenuOption(
                key=f"bot{player_num}",
                label=f"Player {player_num} ({colour})",
                description=make_bot_description,
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
        cfg_key = f"cfg_{field_name}"
        cfg_choices = list(meta.choices)
        options.append(
            MenuOption(
                key=cfg_key,
                label=meta.label,
                description=meta.description,
                choices=cfg_choices,
                default_index=_saved_index(cfg_choices, s.get(cfg_key), meta.default_choice),
                visible_when=not_campaign,
            )
        )

    options.append(
        MenuOption(
            key="campaign_start",
            label="Campaign Start",
            description="Which campaign level to start from.",
            choices=campaign_levels,
            default_index=_saved_index(campaign_levels, s.get("campaign_start"), 0),
            visible_when=lambda v: v["mode"] == "campaign",
        ),
    )

    return options


def _run_gui_menu() -> None:
    """Show the GUI menu and launch the selected game."""
    from clauralux.renderer.menu import MenuScreen

    saved = _load_settings()
    options = _build_menu_options(saved)
    menu = MenuScreen(options)
    result = menu.run()

    if result is None:
        return  # user quit

    _save_settings(result)

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


def _run_visual(
    config: GameConfig,
    map_name: str,
    bot_names: list[str],
    seed: int | None,
    record_path: str | None = None,
) -> None:
    from clauralux.replay.recorder import GameRecorder, save_replay
    from clauralux.runner.visual import VisualRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names, seed)
    bot_name_map = {PlayerId(i + 1): name for i, name in enumerate(bot_names)}
    recorder = GameRecorder(config, state, bot_name_map) if record_path else None
    print(f"Watching: {' vs '.join(bot_names)} on {map_name}")
    if record_path:
        print(f"Recording to: {record_path}")
    print("Controls: Space=pause, Up/Down=speed, Q=quit")
    runner = VisualRunner(config, state, bots, bot_names=bot_name_map, recorder=recorder)
    result = runner.run()
    _print_result(result, bot_names)
    if recorder and record_path:
        replay = recorder.finish(result.winner, result.ticks, result.is_draw)
        save_replay(replay, record_path)
        print(f"Replay saved to: {record_path}")


def _run_headless(
    config: GameConfig,
    map_name: str,
    bot_names: list[str],
    seed: int | None,
    record_path: str | None = None,
) -> None:
    from clauralux.replay.recorder import GameRecorder, save_replay
    from clauralux.runner.headless import HeadlessRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names, seed)
    bot_name_map = {PlayerId(i + 1): name for i, name in enumerate(bot_names)}
    recorder = GameRecorder(config, state, bot_name_map) if record_path else None
    print(f"Running: {' vs '.join(bot_names)} on {map_name}")
    runner = HeadlessRunner(config, state, bots, recorder=recorder)
    result = runner.run()
    _print_result(result, bot_names)
    if recorder and record_path:
        replay = recorder.finish(result.winner, result.ticks, result.is_draw)
        save_replay(replay, record_path)
        print(f"Replay saved to: {record_path}")


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
        config = base_config.replace(**level.config_overrides)
        state = level.map_factory(config)

        # Build bots: P1 is the user's choice, rest from level definition.
        bots: dict[PlayerId, Bot] = {PlayerId(1): make_bot(p1_bot_name)}
        for pid, bot_name in level.enemy_bots.items():
            bots[pid] = make_bot(bot_name)

        enemies = ", ".join(f"P{pid}={name}" for pid, name in level.enemy_bots.items())
        print(f"\nLevel {i}: {level.name}")
        print(f"  {level.description}")
        print(f"  Enemies: {enemies}")

        campaign_bot_names = {PlayerId(1): p1_bot_name}
        for pid, bname in level.enemy_bots.items():
            campaign_bot_names[pid] = bname

        if args.headless:
            from clauralux.runner.headless import HeadlessRunner

            result = HeadlessRunner(config, state, bots).run()
        else:
            print("  Controls: Space=pause, Up/Down=speed, Q=quit")
            result = VisualRunner(config, state, bots, bot_names=campaign_bot_names).run()

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

    print("Running pre-training benchmark...")
    before = _run_benchmark_core(args.benchmark_games)
    _print_benchmark("Pre-training benchmark", before)
    print()

    config = TrainingConfig(
        population_size=args.population,
        generations=args.generations,
        games_per_eval=args.games_per_eval,
        workers=args.workers,
        output_path=args.output,
        from_scratch=args.from_scratch,
        self_play=args.self_play,
    )
    train(config)

    print("\nRunning post-training benchmark...")
    after = _run_benchmark_core(args.benchmark_games)
    _print_benchmark_comparison(before, after)


def _run_megatrain(args: argparse.Namespace) -> None:
    from clauralux.training.trainer import TrainingConfig, train

    output = args.output
    workers = args.workers
    from_scratch = args.from_scratch

    phases = [
        (
            "Phase 1: Train vs hand-crafted bots",
            TrainingConfig(
                population_size=150,
                generations=500,
                games_per_eval=80,
                workers=workers,
                output_path=output,
                from_scratch=from_scratch,
                elite_count=10,
                hall_of_fame_interval=3,
                stagnation_limit=10,
                stagnation_inject=0.25,
            ),
        ),
        (
            "Phase 2: Self-play refinement",
            TrainingConfig(
                population_size=150,
                generations=300,
                games_per_eval=80,
                workers=workers,
                output_path=output,
                self_play=True,
                elite_count=10,
                hall_of_fame_interval=3,
                stagnation_limit=10,
                stagnation_inject=0.25,
            ),
        ),
        (
            "Phase 3: Final polish vs hand-crafted bots",
            TrainingConfig(
                population_size=150,
                generations=200,
                games_per_eval=80,
                workers=workers,
                output_path=output,
                elite_count=10,
                hall_of_fame_interval=3,
                stagnation_limit=10,
                stagnation_inject=0.25,
            ),
        ),
    ]

    print("=" * 60)
    print("MEGATRAIN — no-holds-barred evolved bot training")
    print("  3 phases, 1000 total generations, pop=150, games/eval=80")
    print(f"  Output: {output}")
    print("=" * 60)

    print("\nRunning pre-training benchmark...")
    before = _run_benchmark_core(50)
    _print_benchmark("Pre-training benchmark", before)

    for label, config in phases:
        print(f"\n{'─' * 60}")
        print(label)
        print(f"{'─' * 60}")
        train(config)

    print("\nRunning post-training benchmark...")
    after = _run_benchmark_core(50)
    _print_benchmark_comparison(before, after)


@dataclass
class BenchmarkResult:
    """Results of benchmarking the evolved bot against all opponents."""

    # Per-opponent: {name: (wins, draws, losses)}
    per_opponent: dict[str, tuple[int, int, int]]
    games_per_opponent: int

    @property
    def total_wins(self) -> int:
        return sum(w for w, _d, _l in self.per_opponent.values())

    @property
    def total_draws(self) -> int:
        return sum(d for _w, d, _l in self.per_opponent.values())

    @property
    def total_losses(self) -> int:
        return sum(ls for _w, _d, ls in self.per_opponent.values())

    @property
    def total_games(self) -> int:
        return self.total_wins + self.total_draws + self.total_losses

    @property
    def overall_win_pct(self) -> float:
        return self.total_wins / max(self.total_games, 1) * 100

    def win_pct(self, name: str) -> float:
        w, d, ls = self.per_opponent[name]
        total = w + d + ls
        return w / max(total, 1) * 100


def _run_benchmark_core(games_per_opponent: int) -> BenchmarkResult:
    """Run the evolved bot against all opponents, return structured results."""
    from clauralux.bots.registry import BOT_REGISTRY
    from clauralux.engine.mapgen import generate_map
    from clauralux.runner.tournament import run_tournament

    config = GameConfig(max_ticks=10_000)
    opponents = [name for name in BOT_REGISTRY if name not in ("passive", "evolved")]

    map_factories: list[MapFactory] = [two_player_simple]
    for flavour in FLAVOUR_NAMES:

        def _make_map_factory(f: str) -> MapFactory:
            def factory(cfg: GameConfig) -> GameState:
                return generate_map(cfg, f, 2)

            return factory

        map_factories.append(_make_map_factory(flavour))

    def _make_bot_factory(name: str) -> Callable[[PlayerId], Bot]:
        def factory(_pid: PlayerId) -> Bot:
            return make_bot(name)

        return factory

    per_opponent: dict[str, tuple[int, int, int]] = {}

    for opp_name in opponents:
        opp_wins = 0
        opp_losses = 0
        opp_draws = 0

        for map_factory in map_factories:
            result = run_tournament(
                config=config,
                map_factory=map_factory,
                bot_factories={
                    PlayerId(1): _make_bot_factory("evolved"),
                    PlayerId(2): _make_bot_factory(opp_name),
                },
                num_games=games_per_opponent,
            )
            opp_wins += result.wins.get(PlayerId(1), 0)
            opp_losses += result.wins.get(PlayerId(2), 0)
            opp_draws += result.draws

        per_opponent[opp_name] = (opp_wins, opp_draws, opp_losses)

    return BenchmarkResult(
        per_opponent=per_opponent,
        games_per_opponent=games_per_opponent,
    )


def _print_benchmark(label: str, result: BenchmarkResult) -> None:
    """Print a standalone benchmark table."""
    print(f"{label} ({result.games_per_opponent} games per opponent per map)")
    print("=" * 60)
    for name, (w, d, ls) in result.per_opponent.items():
        pct = result.win_pct(name)
        print(f"  vs {name:<14s}  {w:3d}W {d:3d}D {ls:3d}L  ({pct:5.1f}%)")
    print("=" * 60)
    print(
        f"  Overall: {result.total_wins}W {result.total_draws}D "
        f"{result.total_losses}L / {result.total_games} games "
        f"({result.overall_win_pct:.1f}% win rate)"
    )


def _print_benchmark_comparison(before: BenchmarkResult, after: BenchmarkResult) -> None:
    """Print a side-by-side before/after comparison."""
    print()
    print("=" * 70)
    print("TRAINING RESULTS — Before vs After")
    print("=" * 70)
    print(f"  {'Opponent':<14s}  {'Before':>7s}  {'After':>7s}  {'Change':>8s}")
    print(f"  {'─' * 14}  {'─' * 7}  {'─' * 7}  {'─' * 8}")

    for name in before.per_opponent:
        before_pct = before.win_pct(name)
        after_pct = after.win_pct(name)
        delta = after_pct - before_pct
        if delta > 0:
            arrow = f"+{delta:5.1f}%"
        elif delta < 0:
            arrow = f"{delta:5.1f}%"
        else:
            arrow = "     —"
        print(f"  {name:<14s}  {before_pct:6.1f}%  {after_pct:6.1f}%  {arrow}")

    print(f"  {'─' * 14}  {'─' * 7}  {'─' * 7}  {'─' * 8}")
    before_overall = before.overall_win_pct
    after_overall = after.overall_win_pct
    delta = after_overall - before_overall
    if delta > 0:
        arrow = f"+{delta:5.1f}%"
    elif delta < 0:
        arrow = f"{delta:5.1f}%"
    else:
        arrow = "     —"
    print(f"  {'OVERALL':<14s}  {before_overall:6.1f}%  {after_overall:6.1f}%  {arrow}")
    print("=" * 70)


def _run_benchmark(args: argparse.Namespace) -> None:
    result = _run_benchmark_core(args.benchmark_games)
    _print_benchmark("Evolved Bot Benchmark", result)


def _run_replay(args: argparse.Namespace) -> None:
    from clauralux.replay.recorder import load_replay, replay_to_game
    from clauralux.replay.replay_bot import ReplayBot
    from clauralux.runner.visual import VisualRunner

    replay_file = args.replay_file
    if not replay_file:
        print("Usage: clauralux replay <file.json>")
        sys.exit(1)

    print(f"Loading replay: {replay_file}")
    data = load_replay(replay_file)
    config, state, schedule = replay_to_game(data)

    # Build ReplayBot instances for each player.
    bots: dict[PlayerId, Bot] = {}
    bot_name_map: dict[PlayerId, str] = {}
    for pid_str, name in data.bot_names.items():
        pid = PlayerId(int(pid_str))
        player_schedule = schedule.get(int(pid), [])
        bots[pid] = ReplayBot(player_schedule, bot_name=name)
        bot_name_map[pid] = name

    # If bot_names is empty, infer from state.
    if not bots:
        for p in state.players:
            pid = PlayerId(int(p))
            player_schedule = schedule.get(int(pid), [])
            bots[pid] = ReplayBot(player_schedule)
            bot_name_map[pid] = "unknown"

    result_info = data.result
    print(f"Replaying: {' vs '.join(bot_name_map.values())}")
    print(f"Original result: winner=P{result_info.get('winner')}, ticks={result_info.get('ticks')}")
    print("Controls: Space=pause, Up/Down=speed, Q=quit")

    runner = VisualRunner(config, state, bots, bot_names=bot_name_map)
    result = runner.run()
    bot_names_list = [bot_name_map.get(PlayerId(i + 1), "?") for i in range(len(bots))]
    _print_result(result, bot_names_list)


def _print_result(result: GameResult, bot_names: list[str]) -> None:
    if result.is_draw:
        print(f"  Draw after {result.ticks} ticks")
    else:
        winner_idx = int(result.winner) - 1 if result.winner is not None else -1
        if 0 <= winner_idx < len(bot_names):
            print(f"  P{result.winner} ({bot_names[winner_idx]}) wins in {result.ticks} ticks")
        else:
            print(f"  P{result.winner} wins in {result.ticks} ticks")
