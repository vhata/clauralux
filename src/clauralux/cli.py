from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clauralux.runner.tournament import TournamentResult

import click

from clauralux.bots.base import Bot
from clauralux.bots.registry import BOT_DESCRIPTIONS, BOT_REGISTRY
from clauralux.engine.campaign import CAMPAIGN_LEVELS
from clauralux.engine.config import CONFIG_FIELD_META, GameConfig
from clauralux.engine.mapgen import FLAVOURS, flavour_config, generate_map
from clauralux.engine.maps import (
    five_player_pentagon,
    four_player_cross,
    six_player_hex,
    the_archipelago,
    the_arena,
    the_bridge,
    the_corridor,
    the_crossroads,
    the_diamond,
    the_fortress,
    the_grid,
    the_kingdoms,
    the_ring,
    the_spiral,
    the_web,
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
    "grid": the_grid,
    "fortress": the_fortress,
    "bridge": the_bridge,
    "ring": the_ring,
    "corridor": the_corridor,
    "archipelago": the_archipelago,
    "spiral": the_spiral,
    "diamond": the_diamond,
    "crossroads": the_crossroads,
    "arena": the_arena,
    "web": the_web,
    "kingdoms": the_kingdoms,
}

# Player count for each map. Random maps derive from --players or bot count.
MAP_PLAYER_COUNTS: dict[str, int] = {
    "2p": 2,
    "3p": 3,
    "4p": 4,
    "5p": 5,
    "6p": 6,
    "grid": 2,
    "fortress": 2,
    "bridge": 2,
    "ring": 2,
    "corridor": 2,
    "archipelago": 2,
    "spiral": 2,
    "diamond": 2,
    "crossroads": 3,
    "arena": 4,
    "web": 3,
    "kingdoms": 4,
}

FLAVOUR_NAMES = list(FLAVOURS.keys())

_CONFIG_DIR = Path.home() / ".config" / "clauralux"
_SETTINGS_PATH = _CONFIG_DIR / "settings.json"

_BOT_NAMES_STR = ", ".join(BOT_REGISTRY)
_MAP_NAMES_STR = ", ".join(MAP_REGISTRY)


# ── Click CLI ───────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Clauralux — an Auralux clone for bot strategy development."""
    if ctx.invoked_subcommand is None:
        _run_gui_menu()


def _game_options(f: Callable[..., None]) -> Callable[..., None]:
    """Shared options for watch/headless/tournament commands."""
    f = click.option(
        "--bot",
        "-b",
        "bot",
        multiple=True,
        help=f"Bot type (repeat for each player). Available: {_BOT_NAMES_STR}",
    )(f)
    f = click.option(
        "--map",
        "-m",
        "map_name",
        default="2p",
        help=f"Map: {_MAP_NAMES_STR} or random:FLAVOUR ({', '.join(FLAVOUR_NAMES)})",
    )(f)
    f = click.option("--players", type=int, default=None, help="Players for random maps.")(f)
    f = click.option("--seed", type=int, default=None, help="Random seed for map generation.")(f)
    f = click.option("--max-ticks", type=int, default=30000, help="Max ticks before draw.")(f)
    f = click.option("--speed", type=float, default=2.0, help="Unit speed.")(f)
    return f


@main.command()
@_game_options
@click.option("--record", default=None, metavar="FILE", help="Record game to replay JSON file.")
@click.option("--no-commentary", is_flag=True, help="Disable commentary overlay.")
@click.option("--pause-on-events", is_flag=True, help="Pause on big moments with commentary.")
@click.option("--colorblind", is_flag=True, help="Use colorblind-safe palette.")
def watch(
    bot: tuple[str, ...],
    map_name: str,
    players: int | None,
    seed: int | None,
    max_ticks: int,
    speed: float,
    record: str | None,
    no_commentary: bool,
    pause_on_events: bool,
    colorblind: bool,
) -> None:
    """Watch a game with visual rendering and commentary."""
    config = GameConfig(max_ticks=max_ticks, unit_speed=speed)
    bot_names = _resolve_bots_and_map(list(bot), map_name, players, config)
    if map_name.startswith("random:"):
        config = flavour_config(config, map_name.split(":", 1)[1])
    if colorblind:
        from clauralux.renderer.colors import set_colorblind_mode

        set_colorblind_mode(True)
    _run_visual(
        config,
        map_name,
        bot_names,
        seed,
        record_path=record,
        commentary_enabled=not no_commentary,
        pause_on_events=pause_on_events,
    )


@main.command()
@click.option(
    "--vs",
    "enemies",
    multiple=True,
    help="Enemy bot type (repeat for multiple). Omit for guided selection.",
)
@click.option("--vibe", default=None, help="Map vibe: open, tight, fortified, swarming.")
def play(enemies: tuple[str, ...], vibe: str | None) -> None:
    """Play a quick game as a human. Guided setup if no flags given."""
    enemy_list, map_flavour = _play_guided(list(enemies), vibe)
    num_players = len(enemy_list) + 1
    config = GameConfig(max_ticks=30000)
    config = flavour_config(config, map_flavour)
    state = generate_map(config, map_flavour, num_players)
    bots: dict[PlayerId, Bot] = {PlayerId(1): make_bot("human")}
    bot_name_map: dict[PlayerId, str] = {PlayerId(1): "human"}
    for i, enemy_name in enumerate(enemy_list):
        pid = PlayerId(i + 2)
        bots[pid] = make_bot(enemy_name)
        bot_name_map[pid] = enemy_name
    from clauralux.runner.visual import VisualRunner

    click.echo(f"\nYou vs {', '.join(enemy_list)} on a {map_flavour} map. Let's go!")
    click.echo("Controls: Click to select/send, Shift+click for half, right-click deselect")
    runner = VisualRunner(
        config,
        state,
        bots,
        bot_names=bot_name_map,
        commentary_enabled=True,
        pause_on_events=True,
    )
    result = runner.run()
    _print_result(result, ["human", *enemy_list])


# ── Play mode: interactive guided setup ─────────────────────────────────

_DIFFICULTY_PRESETS: dict[str, list[list[str]]] = {
    "easy": [
        ["passive"],
        ["random"],
        ["passive", "random"],
    ],
    "medium": [
        ["expander"],
        ["rush"],
        ["turtle"],
        ["expander", "random"],
    ],
    "hard": [
        ["aggressive"],
        ["sniper"],
        ["baiter"],
        ["economic"],
        ["coordinator"],
        ["aggressive", "expander"],
    ],
    "brutal": [
        ["evolved"],
        ["neural"],
        ["aggressive", "aggressive"],
        ["sniper", "baiter"],
        ["evolved", "aggressive"],
    ],
}

_VIBE_MAP: dict[str, str] = {
    "open": "strategic",
    "tight": "rush",
    "fortified": "chokepoint",
    "swarming": "swarm",
}


def _play_guided(enemies: list[str], vibe: str | None) -> tuple[list[str], str]:
    """Interactive setup for play mode. Returns (enemy_list, map_flavour)."""
    import random as _rng

    # If enemies already specified, skip difficulty selection.
    if not enemies:
        click.echo()
        click.echo("  HOW TOUGH DO YOU WANT IT?")
        click.echo()
        click.echo("  1. Easy      — gentle opponents, great for learning")
        click.echo("  2. Medium    — a fair challenge, tests your skills")
        click.echo("  3. Hard      — specialist bots that exploit weaknesses")
        click.echo("  4. Brutal    — the toughest bots, trained or paired up")
        click.echo("  5. Surprise  — dealer's choice!")
        click.echo()
        choice = click.prompt("  Pick a number", type=click.IntRange(1, 5), default=2)
        if choice == 5:
            difficulty = _rng.choice(["easy", "medium", "hard", "brutal"])
        else:
            difficulty = ["easy", "medium", "hard", "brutal"][choice - 1]
        enemies = list(_rng.choice(_DIFFICULTY_PRESETS[difficulty]))
        click.echo(f"  → {', '.join(enemies).title()}")

    # If vibe not specified, ask.
    if vibe is None:
        click.echo()
        click.echo("  WHAT KIND OF MAP?")
        click.echo()
        click.echo("  1. Open      — big map, lots of room to expand")
        click.echo("  2. Tight     — close quarters, fast and aggressive")
        click.echo("  3. Fortified — key chokepoints to fight over")
        click.echo("  4. Swarming  — tons of small suns, constant action")
        click.echo("  5. Surprise  — random!")
        click.echo()
        choice = click.prompt("  Pick a number", type=click.IntRange(1, 5), default=5)
        if choice == 5:
            vibe = _rng.choice(list(_VIBE_MAP.keys()))
        else:
            vibe = list(_VIBE_MAP.keys())[choice - 1]
        click.echo(f"  → {vibe.title()}")

    map_flavour = _VIBE_MAP.get(vibe, vibe)
    if map_flavour not in FLAVOURS:
        click.echo(f"Unknown vibe: {vibe}. Using 'strategic'.")
        map_flavour = "strategic"

    return enemies, map_flavour


@main.command()
@_game_options
@click.option("--record", default=None, metavar="FILE", help="Record game to replay JSON file.")
def headless(
    bot: tuple[str, ...],
    map_name: str,
    players: int | None,
    seed: int | None,
    max_ticks: int,
    speed: float,
    record: str | None,
) -> None:
    """Run a game headlessly (fast, no display)."""
    config = GameConfig(max_ticks=max_ticks, unit_speed=speed)
    bot_names = _resolve_bots_and_map(list(bot), map_name, players, config)
    if map_name.startswith("random:"):
        config = flavour_config(config, map_name.split(":", 1)[1])
    _run_headless(config, map_name, bot_names, seed, record_path=record)


@main.command()
@_game_options
@click.option("--games", type=int, default=100, help="Number of games.")
@click.option(
    "--output", "-o", "output_path", default=None, help="Save results to file (.json or .csv)."
)
def tournament(
    bot: tuple[str, ...],
    map_name: str,
    players: int | None,
    seed: int | None,
    max_ticks: int,
    speed: float,
    games: int,
    output_path: str | None,
) -> None:
    """Run a tournament of multiple games and compare win rates."""
    config = GameConfig(max_ticks=max_ticks, unit_speed=speed)
    bot_names = _resolve_bots_and_map(list(bot), map_name, players, config)
    if map_name.startswith("random:"):
        config = flavour_config(config, map_name.split(":", 1)[1])
    _run_tournament(config, map_name, bot_names, games, seed, output_path)


@main.command()
@click.option(
    "--bot",
    "-b",
    "bot_name",
    default="human",
    help=f"Bot for player 1 (default: human). Available: {_BOT_NAMES_STR}",
)
@click.option("--level", type=int, default=1, help="Campaign starting level.")
@click.option("--max-ticks", type=int, default=30000, help="Max ticks before draw.")
@click.option("--speed", type=float, default=2.0, help="Unit speed.")
@click.option("--headless", "run_headless", is_flag=True, help="Run campaign without display.")
def campaign(
    bot_name: str,
    level: int,
    max_ticks: int,
    speed: float,
    run_headless: bool,
) -> None:
    """Play through the 18-level campaign."""
    _run_campaign(
        bot_name=bot_name,
        start_level=level,
        max_ticks=max_ticks,
        speed=speed,
        headless=run_headless,
    )


@main.command()
@click.option("--population", type=int, default=80, help="Population size.")
@click.option("--generations", type=int, default=200, help="Number of generations.")
@click.option("--games-per-eval", type=int, default=40, help="Games per fitness evaluation.")
@click.option("--workers", type=int, default=0, help="Parallel workers (0 = all CPUs).")
@click.option("--output", default="data/evolved_weights.json", help="Output path for weights.")
@click.option("--from-scratch", is_flag=True, help="Ignore existing weights.")
@click.option("--self-play", is_flag=True, help="Train only against other evolved bots.")
@click.option("--neural", is_flag=True, help="Train a neural net bot instead of phase-based.")
@click.option("--benchmark-games", type=int, default=50, help="Games per opponent for benchmark.")
def train(
    population: int,
    generations: int,
    games_per_eval: int,
    workers: int,
    output: str,
    from_scratch: bool,
    self_play: bool,
    neural: bool,
    benchmark_games: int,
) -> None:
    """Train the evolved bot using evolutionary optimisation."""
    if neural and output == "data/evolved_weights.json":
        output = "data/neural_weights.json"
    _run_train(
        population=population,
        generations=generations,
        games_per_eval=games_per_eval,
        workers=workers,
        output=output,
        from_scratch=from_scratch,
        self_play=self_play,
        neural=neural,
        benchmark_games=benchmark_games,
    )


@main.command()
@click.option("--workers", type=int, default=0, help="Parallel workers (0 = all CPUs).")
@click.option("--output", default="data/evolved_weights.json", help="Output path for weights.")
@click.option("--from-scratch", is_flag=True, help="Ignore existing weights.")
@click.option("--neural", is_flag=True, help="Train a neural net bot instead of phase-based.")
def megatrain(workers: int, output: str, from_scratch: bool, neural: bool) -> None:
    """Intensive 3-phase training with automatic benchmarking."""
    if neural and output == "data/evolved_weights.json":
        output = "data/neural_weights.json"
    _run_megatrain(workers=workers, output=output, from_scratch=from_scratch, neural=neural)


@main.command()
@click.option("--benchmark-games", type=int, default=50, help="Games per opponent per map.")
@click.option("--neural", is_flag=True, help="Benchmark the neural bot instead of evolved.")
@click.option(
    "--output", "-o", "output_path", default=None, help="Save results to file (.json or .csv)."
)
def benchmark(benchmark_games: int, neural: bool, output_path: str | None) -> None:
    """Benchmark the evolved bot against all opponents."""
    bot_name = "neural" if neural else "evolved"
    result = _run_benchmark_core(benchmark_games, bot_name=bot_name)
    label = "Neural Bot Benchmark" if neural else "Evolved Bot Benchmark"
    _print_benchmark(label, result)
    if output_path:
        _save_benchmark_results(output_path, result)


@main.command()
@click.option("--games", type=int, default=20, help="Games per matchup (spread across maps).")
@click.option("--output", "-o", "output_path", default="data/analysis.json", help="Output file.")
def analyze(games: int, output_path: str) -> None:
    """Run all-vs-all bot matchups and diagnose weaknesses."""
    from clauralux.analysis import (
        diagnose_weaknesses,
        matchups_to_json,
        run_matchup_matrix,
        save_analysis,
    )

    bot_names = [n for n in BOT_REGISTRY if n not in {"passive", "human", "evolved", "neural"}]
    n_matchups = len(bot_names) * (len(bot_names) - 1) // 2
    click.echo(f"Analyzing {len(bot_names)} bots ({n_matchups} matchups, {games} games each)")

    matchups = run_matchup_matrix(games_per_matchup=games, bot_names=bot_names)
    weaknesses = diagnose_weaknesses(matchups)

    # Print win rate matrix.
    click.echo("\nWin Rate Matrix (row vs column):")
    header = f"{'':>14s}" + "".join(f"{n[:6]:>8s}" for n in bot_names)
    click.echo(header)
    data = matchups_to_json(matchups, weaknesses)
    matrix = data["win_rate_matrix"]
    for name in bot_names:
        row = f"{name:>14s}"
        for opp in bot_names:
            if name == opp:
                row += "      - "
            else:
                pct = matrix.get(name, {}).get(opp, 0.0)
                row += f"{pct:7.1f}%"
        click.echo(row)

    # Print weaknesses.
    if weaknesses:
        click.echo(f"\nDiagnosed Weaknesses ({len(weaknesses)}):")
        for w in weaknesses:
            click.echo(f"  {w.bot} vs {w.opponent} ({w.win_pct:.0f}%): {w.diagnosis}")
    else:
        click.echo("\nNo significant weaknesses found.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    save_analysis(data, output_path)
    click.echo(f"\nFull results saved to {output_path}")


@main.command()
@click.argument("replay_file", type=click.Path(exists=True))
def replay(replay_file: str) -> None:
    """Play back a recorded game."""
    _run_replay(replay_file)


# ── Bot & map resolution ────────────────────────────────────────────────


def _resolve_bots_and_map(
    bot_names: list[str],
    map_name: str,
    players: int | None,
    config: GameConfig,
) -> list[str]:
    """Resolve bot names and validate against map player count."""
    if map_name.startswith("random:"):
        flavour = map_name.split(":", 1)[1]
        if flavour not in FLAVOURS:
            click.echo(f"Unknown flavour: {flavour}. Available: {', '.join(FLAVOUR_NAMES)}")
            sys.exit(1)
        num_players = players or len(bot_names) or 2
        if not bot_names:
            bot_names = ["aggressive", "expander"][:num_players]
            if num_players == 3:
                bot_names = ["aggressive", "expander", "random"]
        if len(bot_names) != num_players:
            click.echo(
                f"Need {num_players} bots for {num_players}-player map, got {len(bot_names)}"
            )
            sys.exit(1)
    elif map_name in MAP_PLAYER_COUNTS:
        expected = MAP_PLAYER_COUNTS[map_name]
        if not bot_names:
            if expected == 3:
                bot_names = ["aggressive", "expander", "random"]
            else:
                bot_names = ["aggressive", "expander"]
        if len(bot_names) != expected:
            click.echo(f"{expected}-player map requires exactly {expected} bots")
            sys.exit(1)
    else:
        if not bot_names:
            bot_names = ["aggressive", "expander"]
        if len(bot_names) != 2:
            click.echo("2-player map requires exactly 2 bots")
            sys.exit(1)
    return bot_names


# ── Settings persistence ────────────────────────────────────────────────


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


# ── Menu helpers ────────────────────────────────────────────────────────


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
        click.echo(f"Unknown bot: {name}. Available: {', '.join(BOT_REGISTRY)}")
        sys.exit(1)
    return cls()


# ── GUI menu ────────────────────────────────────────────────────────────


def _get_player_count_for_map(map_value: str) -> int:
    """Derive player count from a map selection."""
    if map_value in MAP_PLAYER_COUNTS:
        return MAP_PLAYER_COUNTS[map_value]
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

    commentary_choices = ["On", "Off"]
    pause_events_choices = ["Off", "On"]
    options.append(
        MenuOption(
            key="commentary",
            label="Commentary",
            description="Sports-commentator text overlay describing the action.",
            choices=commentary_choices,
            default_index=_saved_index(commentary_choices, s.get("commentary"), 0),
            visible_when=lambda v: v["mode"] == "watch",
        ),
    )
    options.append(
        MenuOption(
            key="pause_on_events",
            label="Pause on Events",
            description="Pause on big moments (captures, eliminations) with commentary.",
            choices=pause_events_choices,
            default_index=_saved_index(pause_events_choices, s.get("pause_on_events"), 0),
            visible_when=lambda v: v["mode"] == "watch" and v.get("commentary") == "On",
        ),
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

    colorblind_choices = ["Off", "On"]
    options.append(
        MenuOption(
            key="colorblind",
            label="Colorblind Mode",
            description="Use colorblind-safe palette (avoids red-green confusion).",
            choices=colorblind_choices,
            default_index=_saved_index(colorblind_choices, s.get("colorblind"), 0),
            visible_when=lambda v: v["mode"] in ("watch", "campaign"),
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

    if result.get("colorblind") == "On":
        from clauralux.renderer.colors import set_colorblind_mode

        set_colorblind_mode(True)

    if mode == "campaign":
        campaign_start_str = result.get("campaign_start", "1. First Light")
        campaign_start = int(campaign_start_str.split(".")[0])
        _run_campaign(
            bot_name=bot_names[0],
            start_level=campaign_start,
            max_ticks=config.max_ticks or 30000,
            speed=config.unit_speed,
            headless=False,
        )
    elif mode == "watch":
        commentary_enabled = result.get("commentary", "On") == "On"
        pause_on_events = result.get("pause_on_events", "Off") == "On"
        _run_visual(
            config,
            map_name,
            bot_names,
            None,
            commentary_enabled=commentary_enabled,
            pause_on_events=pause_on_events,
        )
    elif mode == "headless":
        _run_headless(config, map_name, bot_names, None)
    elif mode == "tournament":
        _run_tournament(config, map_name, bot_names, 100, None)


# ── Game runners ────────────────────────────────────────────────────────


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
    commentary_enabled: bool = True,
    pause_on_events: bool = False,
) -> None:
    from clauralux.replay.recorder import GameRecorder, save_replay
    from clauralux.runner.visual import VisualRunner

    state, bots = _make_state_and_bots(config, map_name, bot_names, seed)
    bot_name_map = {PlayerId(i + 1): name for i, name in enumerate(bot_names)}
    recorder = GameRecorder(config, state, bot_name_map) if record_path else None
    click.echo(f"Watching: {' vs '.join(bot_names)} on {map_name}")
    if record_path:
        click.echo(f"Recording to: {record_path}")
    click.echo("Controls: Space/Enter=pause, Up/Down=speed, Q=quit")
    runner = VisualRunner(
        config,
        state,
        bots,
        bot_names=bot_name_map,
        recorder=recorder,
        commentary_enabled=commentary_enabled,
        pause_on_events=pause_on_events,
    )
    result = runner.run()
    _print_result(result, bot_names)
    if recorder and record_path:
        replay_data = recorder.finish(result.winner, result.ticks, result.is_draw)
        save_replay(replay_data, record_path)
        click.echo(f"Replay saved to: {record_path}")


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
    click.echo(f"Running: {' vs '.join(bot_names)} on {map_name}")
    runner = HeadlessRunner(config, state, bots, recorder=recorder)
    result = runner.run()
    _print_result(result, bot_names)
    if recorder and record_path:
        replay_data = recorder.finish(result.winner, result.ticks, result.is_draw)
        save_replay(replay_data, record_path)
        click.echo(f"Replay saved to: {record_path}")


def _run_tournament(
    config: GameConfig,
    map_name: str,
    bot_names: list[str],
    num_games: int,
    seed: int | None,
    output_path: str | None = None,
) -> None:
    from clauralux.runner.tournament import run_tournament

    def map_factory(cfg: GameConfig) -> GameState:
        return _resolve_map(cfg, map_name, bot_names, seed)

    bot_factories: dict[PlayerId, Callable[[PlayerId], Bot]] = {}
    for i, name in enumerate(bot_names):
        bot_name = name
        bot_factories[PlayerId(i + 1)] = lambda _pid, bn=bot_name: make_bot(bn)  # type: ignore[misc]

    click.echo(f"Tournament: {' vs '.join(bot_names)} on {map_name}, {num_games} games")
    result = run_tournament(
        config=config,
        map_factory=map_factory,
        bot_factories=bot_factories,
        num_games=num_games,
        rotate_positions=True,
    )

    click.echo(f"\nResults ({result.total_games} games):")
    for i, name in enumerate(bot_names):
        pid = PlayerId(i + 1)
        wins = result.wins.get(pid, 0)
        rate = result.win_rate(pid)
        click.echo(f"  P{pid} ({name}): {wins} wins ({rate:.1%})")
    click.echo(f"  Draws: {result.draws}")
    click.echo(f"  Avg ticks: {result.avg_ticks:.0f}")

    if output_path:
        _save_tournament_results(output_path, bot_names, result)


def _save_tournament_results(
    path: str,
    bot_names: list[str],
    result: TournamentResult,
) -> None:
    """Save tournament results to JSON or CSV file."""

    rows = []
    for i, name in enumerate(bot_names):
        pid = PlayerId(i + 1)
        rows.append(
            {
                "bot": name,
                "wins": result.wins.get(pid, 0),
                "win_rate": round(result.win_rate(pid), 4),
            }
        )

    if path.endswith(".json"):
        import json

        data = {
            "total_games": result.total_games,
            "draws": result.draws,
            "avg_ticks": round(result.avg_ticks, 1),
            "bots": rows,
        }
        Path(path).write_text(json.dumps(data, indent=2) + "\n")
    elif path.endswith(".csv"):
        import csv

        with Path(path).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["bot", "wins", "win_rate"])
            writer.writeheader()
            writer.writerows(rows)
    else:
        click.echo(f"Warning: unknown output format for {path} (use .json or .csv)")
        return

    click.echo(f"Results saved to {path}")


def _save_benchmark_results(path: str, result: BenchmarkResult) -> None:
    """Save benchmark results to JSON or CSV file."""
    rows = []
    for name in sorted(result.per_opponent):
        w, d, ls = result.per_opponent[name]
        rows.append(
            {
                "opponent": name,
                "wins": w,
                "draws": d,
                "losses": ls,
                "win_pct": round(result.win_pct(name), 1),
            }
        )

    if path.endswith(".json"):
        data = {
            "total_games": result.total_games,
            "overall_win_pct": round(result.overall_win_pct, 1),
            "opponents": rows,
        }
        Path(path).write_text(json.dumps(data, indent=2) + "\n")
    elif path.endswith(".csv"):
        import csv

        with Path(path).open("w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["opponent", "wins", "draws", "losses", "win_pct"]
            )
            writer.writeheader()
            writer.writerows(rows)
    else:
        click.echo(f"Warning: unknown output format for {path} (use .json or .csv)")
        return

    click.echo(f"Results saved to {path}")


def _run_campaign(
    bot_name: str,
    start_level: int,
    max_ticks: int,
    speed: float,
    headless: bool,
) -> None:
    from clauralux.runner.visual import VisualRunner

    start = max(1, min(start_level, len(CAMPAIGN_LEVELS)))

    click.echo(f"Campaign: P1 = {bot_name}, starting at level {start}")
    click.echo(f"{'─' * 50}")

    for i, level in enumerate(CAMPAIGN_LEVELS[start - 1 :], start=start):
        base_config = GameConfig(max_ticks=max_ticks, unit_speed=speed)
        config = base_config.replace(**level.config_overrides)
        state = level.map_factory(config)

        # Build bots: P1 is the user's choice, rest from level definition.
        bots: dict[PlayerId, Bot] = {PlayerId(1): make_bot(bot_name)}
        for pid, bname in level.enemy_bots.items():
            bots[pid] = make_bot(bname)

        enemies = ", ".join(f"P{pid}={name}" for pid, name in level.enemy_bots.items())
        click.echo(f"\nLevel {i}: {level.name}")
        click.echo(f"  {level.description}")
        click.echo(f"  Enemies: {enemies}")

        campaign_bot_names = {PlayerId(1): bot_name}
        for pid, bname in level.enemy_bots.items():
            campaign_bot_names[pid] = bname

        if headless:
            from clauralux.runner.headless import HeadlessRunner

            result = HeadlessRunner(config, state, bots).run()
        else:
            click.echo("  Controls: Space=pause, Up/Down=speed, Q=quit")
            result = VisualRunner(config, state, bots, bot_names=campaign_bot_names).run()

        level_bot_names = [bot_name, *level.enemy_bots.values()]
        _print_result(result, level_bot_names)

        if result.winner == PlayerId(1):
            click.echo("  >>> VICTORY! <<<")
        elif result.is_draw:
            click.echo("  >>> DRAW <<<")
        else:
            click.echo("  >>> DEFEAT <<<")
            break

    else:
        click.echo(f"\n{'─' * 50}")
        click.echo("CAMPAIGN COMPLETE!")


def _run_train(
    population: int,
    generations: int,
    games_per_eval: int,
    workers: int,
    output: str,
    from_scratch: bool,
    self_play: bool,
    neural: bool,
    benchmark_games: int,
) -> None:
    from clauralux.training.trainer import TrainingConfig
    from clauralux.training.trainer import train as run_training

    bot_name = "neural" if neural else "evolved"
    click.echo("Running pre-training benchmark...")
    before = _run_benchmark_core(benchmark_games, bot_name=bot_name)
    _print_benchmark("Pre-training benchmark", before)
    click.echo()

    config = TrainingConfig(
        population_size=population,
        generations=generations,
        games_per_eval=games_per_eval,
        workers=workers,
        output_path=output,
        from_scratch=from_scratch,
        self_play=self_play,
        neural=neural,
    )
    run_training(config)

    click.echo("\nRunning post-training benchmark...")
    after = _run_benchmark_core(benchmark_games, bot_name=bot_name)
    _print_benchmark_comparison(before, after)


def _run_megatrain(workers: int, output: str, from_scratch: bool, neural: bool = False) -> None:
    from clauralux.training.trainer import TrainingConfig
    from clauralux.training.trainer import train as run_training

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
                neural=neural,
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
                neural=neural,
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
                neural=neural,
                elite_count=10,
                hall_of_fame_interval=3,
                stagnation_limit=10,
                stagnation_inject=0.25,
            ),
        ),
    ]

    bot_type = "neural" if neural else "evolved"
    click.echo("=" * 60)
    click.echo(f"MEGATRAIN ({bot_type}) — no-holds-barred training")
    click.echo("  3 phases, 1000 total generations, pop=150, games/eval=80")
    click.echo(f"  Output: {output}")
    click.echo("=" * 60)

    bot_name = "neural" if neural else "evolved"
    click.echo("\nRunning pre-training benchmark...")
    before = _run_benchmark_core(50, bot_name=bot_name)
    _print_benchmark("Pre-training benchmark", before)

    for label, config in phases:
        click.echo(f"\n{'─' * 60}")
        click.echo(label)
        click.echo(f"{'─' * 60}")
        run_training(config)

    click.echo("\nRunning post-training benchmark...")
    after = _run_benchmark_core(50, bot_name=bot_name)
    _print_benchmark_comparison(before, after)


# ── Benchmark ───────────────────────────────────────────────────────────


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


def _run_benchmark_core(games_per_opponent: int, bot_name: str = "evolved") -> BenchmarkResult:
    """Run a bot against all opponents, return structured results."""
    from clauralux.bots.registry import BOT_REGISTRY
    from clauralux.engine.mapgen import generate_map
    from clauralux.runner.tournament import run_tournament

    config = GameConfig(max_ticks=10_000)
    excluded = {"passive", "evolved", "neural", "human"}
    opponents = [name for name in BOT_REGISTRY if name not in excluded]

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
                    PlayerId(1): _make_bot_factory(bot_name),
                    PlayerId(2): _make_bot_factory(opp_name),
                },
                num_games=games_per_opponent,
                rotate_positions=True,
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
    click.echo(f"{label} ({result.games_per_opponent} games per opponent per map)")
    click.echo("=" * 60)
    for name, (w, d, ls) in result.per_opponent.items():
        pct = result.win_pct(name)
        click.echo(f"  vs {name:<14s}  {w:3d}W {d:3d}D {ls:3d}L  ({pct:5.1f}%)")
    click.echo("=" * 60)
    click.echo(
        f"  Overall: {result.total_wins}W {result.total_draws}D "
        f"{result.total_losses}L / {result.total_games} games "
        f"({result.overall_win_pct:.1f}% win rate)"
    )


def _print_benchmark_comparison(before: BenchmarkResult, after: BenchmarkResult) -> None:
    """Print a side-by-side before/after comparison."""
    click.echo()
    click.echo("=" * 70)
    click.echo("TRAINING RESULTS — Before vs After")
    click.echo("=" * 70)
    click.echo(f"  {'Opponent':<14s}  {'Before':>7s}  {'After':>7s}  {'Change':>8s}")
    click.echo(f"  {'─' * 14}  {'─' * 7}  {'─' * 7}  {'─' * 8}")

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
        click.echo(f"  {name:<14s}  {before_pct:6.1f}%  {after_pct:6.1f}%  {arrow}")

    click.echo(f"  {'─' * 14}  {'─' * 7}  {'─' * 7}  {'─' * 8}")
    before_overall = before.overall_win_pct
    after_overall = after.overall_win_pct
    delta = after_overall - before_overall
    if delta > 0:
        arrow = f"+{delta:5.1f}%"
    elif delta < 0:
        arrow = f"{delta:5.1f}%"
    else:
        arrow = "     —"
    click.echo(f"  {'OVERALL':<14s}  {before_overall:6.1f}%  {after_overall:6.1f}%  {arrow}")
    click.echo("=" * 70)


# ── Replay ──────────────────────────────────────────────────────────────


def _run_replay(replay_file: str) -> None:
    from clauralux.replay.recorder import load_replay, replay_to_game
    from clauralux.replay.replay_bot import ReplayBot
    from clauralux.runner.visual import VisualRunner

    click.echo(f"Loading replay: {replay_file}")
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
    click.echo(f"Replaying: {' vs '.join(bot_name_map.values())}")
    click.echo(
        f"Original result: winner=P{result_info.get('winner')}, ticks={result_info.get('ticks')}"
    )
    click.echo("Controls: Space=pause, Up/Down=speed, Q=quit")

    runner = VisualRunner(config, state, bots, bot_names=bot_name_map)
    result = runner.run()
    bot_names_list = [bot_name_map.get(PlayerId(i + 1), "?") for i in range(len(bots))]
    _print_result(result, bot_names_list)


# ── Utilities ───────────────────────────────────────────────────────────


def _print_result(result: GameResult, bot_names: list[str]) -> None:
    if result.is_draw:
        click.echo(f"  Draw after {result.ticks} ticks")
    else:
        winner_idx = int(result.winner) - 1 if result.winner is not None else -1
        if 0 <= winner_idx < len(bot_names):
            click.echo(f"  P{result.winner} ({bot_names[winner_idx]}) wins in {result.ticks} ticks")
        else:
            click.echo(f"  P{result.winner} wins in {result.ticks} ticks")
