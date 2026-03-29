# Clauralux Architecture & Developer Guide

Everything you need to know to pick this project up cold and start building on it.

## What Is This?

An Auralux clone built as a bot strategy development platform. The game engine is completely decoupled from rendering — you can run bot-vs-bot games headlessly at full speed, or watch them in a pygame window. The primary use case is writing and testing bot strategies, not playing manually (though human play is a planned feature).

## Game Rules

- A map has **suns** — some owned by players (colour-coded), some neutral
- Owned suns **produce units** over time. Higher-level suns produce faster
- Players **send units** from a sun to any other sun. Units travel as a group
- Units arriving at a **friendly** sun add to its garrison (reinforce)
- Units arriving at an **enemy/neutral** sun subtract from garrison (attack). 1 attacker removes `attack_ratio` defenders. If garrison hits 0, the sun is captured with remaining attackers as the new garrison
- Suns can be **upgraded** (level 1→3) by spending garrison units. Captured suns reset to level 1 (configurable)
- A player is **eliminated** when they have no suns and no units in flight
- **Last player standing wins**. If max ticks is reached, it's a draw

## Architecture: Three Clean Layers

```
┌──────────────────────────────────────────────────┐
│  Runner Layer (headless / visual / tournament)   │
├──────────────────────────────────────────────────┤
│  Bot Layer (base class + 9 implementations)      │
├──────────────────────────────────────────────────┤
│  Engine Layer (pure logic, zero external deps)   │
└──────────────────────────────────────────────────┘
```

**Engine** has zero external dependencies. **Bots** depend only on engine types. **Renderer/Visual runner** depends on pygame-ce (optional dep). This is deliberate — don't break it.

## File Map

### Engine (`src/clauralux/engine/`) — Zero external deps

| File | What | Key types |
|------|------|-----------|
| `types.py` | Primitives | `PlayerId`, `SunId`, `Tick`, `Position`, `NEUTRAL` |
| `config.py` | All tunable parameters | `GameConfig` (frozen dataclass), `CONFIG_FIELD_META` (menu metadata) |
| `state.py` | Mutable game state | `Sun`, `UnitGroup`, `GameState` |
| `actions.py` | What bots can do | `SendUnits`, `UpgradeSun`, `Action` (union type) |
| `game.py` | Tick-based simulation | `Game` class with `tick()`, `apply_actions()`, `get_view()` |
| `view.py` | Read-only snapshot for bots | `GameView`, `SunView`, `UnitGroupView` |
| `maps.py` | Handcrafted map layouts | `two_player_simple`, `three_player_triangle`, `four_player_cross`, `five_player_pentagon`, `six_player_hex` |
| `mapgen.py` | Themed random generation | `generate_map(config, flavour, num_players, seed)`, `flavour_config()` |
| `campaign.py` | 18-level campaign | `CampaignLevel`, `CAMPAIGN_LEVELS` list |

### Bots (`src/clauralux/bots/`)

| File | Strategy | Personality |
|------|----------|-------------|
| `base.py` | Abstract base class | `Bot.decide(view) -> list[Action]`, `Bot.intent` property |
| `passive.py` | Does nothing | "Peacefully existing." |
| `random_bot.py` | Dice rolls | "Dice say send 7 units to Sun 4. Why not." |
| `aggressive.py` | Overwhelm weakest target | Waits until it can overwhelm, then sends everything |
| `expander.py` | Economy first | Grab neutrals → upgrade → attack enemies |
| `turtle.py` | Upgrade and fortify | Max all levels, build garrison, then crush |
| `rush.py` | Constant early pressure | Sends units every 20 ticks at the nearest target |
| `sniper.py` | Eliminate players | Ignores neutrals, targets weakest player's weakest sun |
| `opportunist.py` | Strike the weak | Scores targets by garrison+distance, pounces on low garrisons |
| `evolved.py` | Learned strategy | 26 evolvable parameters trained via evolution against all other bots |

### Renderer (`src/clauralux/renderer/`) — Pygame-ce

| File | What |
|------|------|
| `colors.py` | Player colour palette (6 players), `get_color()`, `get_bright_color()` |
| `renderer.py` | `PygameRenderer` — draws suns (pulsing glow, level rings, garrison count), unit groups (swarm dots), trajectories (dashed lines), capture flashes, HUD (stats, bars, intents, speed) |
| `menu.py` | `MenuOption` (with `visible_when` callback), `MenuScreen` — data-driven GUI menu |

### Runners (`src/clauralux/runner/`)

| File | What |
|------|------|
| `headless.py` | `HeadlessRunner` — fast bot-vs-bot, returns `GameResult` |
| `visual.py` | `VisualRunner` — pygame display, passes intents/speed/pause to renderer |
| `tournament.py` | `run_tournament()` — N games, aggregates win rates |

### Training (`src/clauralux/training/`)

| File | What |
|------|------|
| `genome.py` | Parameter definitions (`ParamSpec`), ranges, JSON serialization |
| `evolution.py` | Evolutionary operators: fitness evaluation, tournament selection, crossover, mutation |
| `trainer.py` | Training loop orchestrator with `ProcessPoolExecutor` parallelism |

The training system operates on raw `list[float]` genomes — it doesn't know whether the floats are heuristic weights or neural network parameters. This makes it reusable for future approaches (neuroevolution, etc.).

### CLI (`src/clauralux/cli.py`)

Entry point. Running `clauralux` with no args shows the GUI menu. CLI commands: `watch`, `headless`, `tournament`, `campaign`.

Key registries (add to these to extend):
- `BOT_REGISTRY: dict[str, type[Bot]]` — add a bot here, it appears in the menu automatically
- `MAP_REGISTRY: dict[str, MapFactory]` — add a map here
- `MAP_PLAYER_COUNTS: dict[str, int]` — player count per map (for menu bot selector visibility)

## How the Tick Loop Works

```
Game.tick():
  1. _process_actions()    — validate & execute queued SendUnits/UpgradeSun
  2. _move_unit_groups()   — advance each group by unit_speed toward target
  3. _resolve_arrivals()   — groups within unit_speed of target: reinforce or attack
  4. _produce_units()      — integer tick counter per sun, spawn unit when threshold hit
  5. _check_win_condition() — eliminate players with no suns & no groups, declare winner
  6. increment tick
```

Actions are queued via `game.apply_actions(player_id, actions)` before each `tick()`. The runner handles polling bots and feeding actions.

## How to Add a New Bot

1. Create `src/clauralux/bots/my_bot.py`:

```python
from clauralux.bots.base import Bot
from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView

class MyBot(Bot):
    def decide(self, view: GameView) -> list[Action]:
        # view.my_suns(), view.enemy_suns(), view.neutral_suns()
        # view.my_unit_groups(), view.config, view.tick
        self._intent = "Thinking about stuff..."
        return []  # or a list of SendUnits/UpgradeSun actions
```

2. Register in `cli.py`:

```python
from clauralux.bots.my_bot import MyBot

BOT_REGISTRY = {
    ...
    "my_bot": MyBot,
}
```

That's it. It appears in the GUI menu and CLI automatically.

## How to Add a New Tunable Parameter

1. Add the field to `GameConfig` in `config.py`:

```python
@dataclass(frozen=True, slots=True)
class GameConfig:
    ...
    my_new_param: float = 1.0
```

2. Add metadata in the same file to expose it in the menu:

```python
CONFIG_FIELD_META = {
    ...
    "my_new_param": ConfigFieldMeta(
        label="My Param",
        description="What this does.",
        choices=["0.5", "1.0 (default)", "2.0"],
        default_choice=1,
    ),
}
```

That's it. The menu auto-generates the option and the config builder parses it.

## How to Add a New Map

1. Add a factory function in `maps.py`:

```python
def my_map(config: GameConfig) -> GameState:
    suns = dict([
        _sun(0, x, y, PlayerId(1), config.default_player_garrison),
        _sun(1, x, y, PlayerId(2), config.default_player_garrison),
        _sun(2, x, y, NEUTRAL, config.default_neutral_garrison),
    ])
    return GameState(suns=suns, players=[PlayerId(1), PlayerId(2)])
```

2. Register in `cli.py`:

```python
MAP_REGISTRY = { ..., "my_map": my_map }
MAP_PLAYER_COUNTS = { ..., "my_map": 2 }
```

For random map flavours, add to `FLAVOURS` dict in `mapgen.py`.

## How to Add a New Map Flavour

Add to `FLAVOURS` in `mapgen.py`:

```python
FLAVOURS = {
    ...
    "my_flavour": FlavourParams(
        total_suns=(8, 12),
        neutral_garrison=(10.0, 20.0),
        min_sun_spacing=80.0,
        player_edge_bias=0.8,
        config_overrides={"production_interval": 25},
    ),
}
```

It appears in the menu as `random:my_flavour` automatically.

## How to Train the Evolved Bot

```bash
uv run clauralux train                    # full run (~10 min)
uv run clauralux train --population 20 --generations 20  # quick test
```

### What the bot actually is

The `EvolvedBot` is a parameterized heuristic bot — the same kind of if/then decision logic as the hand-crafted bots, but with 26 floating-point parameters controlling every threshold and weight. These parameters cover:

- **Target scoring** — how much to weight garrison size, distance, sun level, neutral vs enemy preference, and whether friendly units are already heading there
- **Force commitment** — how many units to keep in reserve, what force ratio is needed before attacking, what fraction to send, whether to concentrate from one sun or split from all
- **Economy** — when to upgrade, how much to prefer upgrading over attacking, how long to focus on economy at the start
- **Timing** — how often to make decisions, how aggressive to be early, how patient to be overall
- **Coordination** — when to reinforce weak suns, how to weigh nearest vs average distance
- **Threat response** — how much to react to incoming enemy units

Different parameter values produce radically different play styles. `w_neutral_bonus = 3.0` makes an expander; `upgrade_vs_attack = 0.95` makes a turtle; `act_interval = 15` with `min_force_ratio = 0.8` makes a rusher.

### How the fitness signal works

Each candidate genome is evaluated by playing it (as Player 1) against the 7 non-passive hand-crafted bots across 3 maps (2p fixed, random:strategic, random:rush). It plays `games_per_eval` games total, cycling through opponents and maps. The fitness score is:

```
fitness = (wins + 0.3 * draws) / total_games
```

A perfect score of 1.0 means it won every game. Draws are worth 0.3 to mildly reward survival without incentivising passive play. Games are capped at 10,000 ticks to penalise stalemates.

### How evolution improves it

The training loop uses a standard evolutionary algorithm:

1. **Initialise** — 50 candidates: one seeded from existing weights (or defaults), the rest random
2. **Evaluate** — run each candidate's games in parallel (`ProcessPoolExecutor`), compute fitness
3. **Select** — tournament selection (pick 3 random candidates, keep the fittest) to choose parents
4. **Crossover** — for each gene, randomly pick from parent A or parent B (uniform crossover)
5. **Mutate** — each gene has a 20% chance of Gaussian noise (sigma = 5% of the parameter's range)
6. **Elitism** — the top 5 candidates survive unchanged into the next generation
7. **Repeat** — mutation sigma decays by 0.5% each generation, narrowing the search over time

The key insight: evolution doesn't need gradients or a differentiable model. It just needs a fitness score and a way to combine and vary candidates. This is why the same training harness can later be used for neural network weights — the algorithm doesn't care what the floats mean.

### Why it might not beat every bot

The fitness signal averages across all opponents. A candidate that beats random/passive/rush 100% of the time but loses to opportunist 50% still scores ~0.85 — which may be higher than a specialist that beats opportunist but struggles elsewhere. This can lead to generalist strategies that plateau. Possible improvements:
- Increase `games_per_eval` for a less noisy signal
- Weight harder opponents more heavily in the fitness score
- Run more generations with larger populations
- Graduate to a neural network brain for more expressive strategies

Trained weights are loaded automatically by `EvolvedBot()`. If no weights file exists, it uses sensible defaults.

## Key Design Decisions

- **Engine has zero deps.** Don't import pygame or anything external in `engine/`. This allows headless testing and fast simulation.
- **Bots see `GameView`, not `GameState`.** GameView is frozen/immutable with integer garrisons. Bots can't cheat by mutating state.
- **Human player is planned as just another Bot.** `HumanBot` would have methods like `select_sun()`, `send_to_sun()` called by the visual runner from pygame events. The bot itself has no pygame dependency.
- **Deterministic simulation.** Same seed + same actions = same outcome. Integer tick counting for production (not float accumulation) to avoid drift.
- **Menu is data-driven.** `MenuOption` has a `visible_when` callback. Bot selectors appear/hide based on map player count. Config options auto-generated from `CONFIG_FIELD_META`.
- **Bot intent narration.** Every bot sets `self._intent` during `decide()` to explain its reasoning. Displayed in the HUD. Eliminated bots show 💀.
- **Flavour configs.** Random maps apply config overrides (e.g. rush = fast production + fast units). `flavour_config()` uses `dataclasses.replace()`.

## What's NOT Built Yet

- **Human player** — `HumanBot` that maps mouse clicks to actions (planned architecture exists in the plan, never implemented)
- **Replay system** — record actions per tick, replay deterministically
- **Bot hot-reloading** — edit a bot, see changes without restarting
- **Sound** — no audio at all
- **Fog of war** — bots see everything currently
- **Network multiplayer** — not even considered
- **Save/load** — no game state persistence

## Tooling

- **uv** for dependency management (`uv sync --group dev --extra visual`)
- **pytest** with coverage (`make test`)
- **ruff** v0.15.8 for linting and formatting (`make format`, `make lint`)
- **mypy** strict mode (`make type`)
- **pre-commit** hooks enforce all of the above on commit
- **pygame-ce** (not pygame) — community edition bundles SDL properly

`make check` runs format check + lint + mypy + tests. Always run before committing.

## Running

```bash
uv run clauralux              # GUI menu
uv run clauralux watch        # bot-vs-bot with defaults
uv run clauralux campaign --bot expander
uv run clauralux headless --bot aggressive --bot turtle
uv run clauralux tournament --bot sniper --bot opportunist --games 100
```

Visual controls: Space = pause, Up/Down = speed (2x steps, shown in HUD), Q = quit.

## Stats

- ~4300 lines of Python
- 84 tests
- 35 source files
- 9 bot strategies (8 hand-crafted + 1 evolved)
- 5 handcrafted maps + 4 random flavours
- 18 campaign levels
- 9 tunable config parameters exposed in menu
