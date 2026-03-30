# Clauralux

An Auralux clone built for bot strategy development. The game engine is completely decoupled from rendering — write bots, pit them against each other headlessly at full speed, or watch them fight in a pygame window with sports commentary.

## How the Game Works

The map contains **suns** — some owned by players (colour-coded), some neutral. Each player starts with one sun.

- **Production**: Owned suns produce units over time. Higher-level suns produce faster.
- **Sending units**: Select units at a sun and send them to any other sun. They travel across the map as a group.
- **Reinforcing**: Units arriving at a friendly sun add to its garrison.
- **Attacking**: Units arriving at an enemy or neutral sun fight the garrison — each attacker removes one defender. If the garrison hits zero, the attacker captures the sun with any remaining units.
- **Upgrading**: Spend garrison units to upgrade a sun's level (up to level 3), increasing its production rate. Captured suns reset to level 1.
- **Winning**: A player is eliminated when they have no suns and no units in flight. Last player standing wins. If the tick limit is reached, it's a draw.

All of these parameters (production speed, attack ratio, upgrade costs, level reset, etc.) are configurable via `GameConfig`.

## Features

- **Bot-first architecture** — engine has zero external dependencies, runs headlessly
- **14 built-in bots** (each with strategic intent narration)
- **Evolutionary training** — train an evolved bot by running `clauralux train` to optimise 25 parameters against all other bots, with difficulty-weighted opponents and stagnation resets
- **Megatrain** — intensive multi-phase training: hand-crafted opponents, self-play refinement, then final polish with automatic before/after benchmarking
- **Benchmark** — scorecard showing evolved bot's win rate against every opponent across all maps
- **Sports commentary** — enthusiastic commentator overlay in watch mode with event detection, floating text annotations, and optional pause-on-big-moments
- **Replay system** — record, save, load, and play back games
- **Themed random maps** — strategic, rush, chokepoint, swarm
- **18-level campaign** — gradual difficulty progression from passive to dual-aggressive enemies
- **Tournament system** — run N games and compare bot win rates
- **GUI menu** — configure and launch games without touching the CLI, with bot strategy descriptions and settings persistence
- **Visual renderer** — pygame-ce with pulsing suns, unit swarms, trajectory lines, capture flashes, and detailed pause overlay

## Bots

| Bot | Strategy |
|-----|----------|
| **passive** | Does nothing. Just sits there. |
| **random** | Picks actions by dice roll. Chaotic and bad. |
| **aggressive** | Waits until it can overwhelm the weakest target, then sends everything. |
| **expander** | Grabs neutrals first, upgrades economy, attacks enemies last. |
| **turtle** | Upgrades all suns to max, builds huge garrisons, then crushes. |
| **rush** | Constant early pressure — sends units every 20 ticks at the nearest target. |
| **sniper** | Ignores neutrals. Targets the weakest player's weakest sun to eliminate them. |
| **opportunist** | Watches for low garrisons and pounces. Upgrades when nothing's weak enough. |
| **swarm** | Many small attacks from every sun. Death by a thousand cuts. |
| **coordinator** | Accumulates, then strikes multiple targets simultaneously. |
| **reactive** | Defensive — reinforces threatened suns, only attacks with overwhelming force. |
| **economic** | Upgrades aggressively, then targets the opponent's highest-level suns. |
| **baiter** | Sends small bait attacks to draw defenders, then hits the weakened suns. |
| **evolved** | Trained by playing thousands of games against all other bots. 25 evolvable parameters covering target selection, force commitment, economy, timing, and threat response. |

## Prerequisites

- Python 3.12+
- Rust toolchain (install: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- uv (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Quickstart

```bash
uv venv .venv
uv sync --group dev --extra visual
uv run maturin develop --release   # Build the Rust engine
uv run pre-commit install

# Launch the GUI menu
uv run clauralux
```

## Usage

### GUI Menu

Just run `uv run clauralux` with no arguments to get a pygame menu where you pick mode, map, bots, and speed.

### CLI

```bash
# Watch a game
clauralux watch --bot aggressive --bot expander

# Watch a random rush map
clauralux watch --map random:rush --bot aggressive --bot expander

# Run headless (fast, no display)
clauralux headless --bot expander --bot aggressive

# Tournament: 100 games, compare win rates
clauralux tournament --bot aggressive --bot expander --games 100

# Campaign: play through 18 levels
clauralux campaign --bot expander

# Campaign: start from level 10, headless
clauralux campaign --bot aggressive --level 10 --headless

# Record a game for replay
clauralux watch --bot evolved --bot sniper --record game.json

# Play back a recorded game
clauralux replay game.json
```

### Training

```bash
# Train the evolved bot (default: pop=80, gens=200, 40 games/eval)
clauralux train

# Train from scratch (ignore existing weights)
clauralux train --from-scratch

# Self-play: train only against other evolved bots
clauralux train --self-play

# Quick training run
clauralux train --population 20 --generations 20 --games-per-eval 10

# Megatrain: intensive 3-phase training with automatic benchmarking
clauralux megatrain --from-scratch

# Benchmark the evolved bot against all opponents
clauralux benchmark
clauralux benchmark --benchmark-games 100
```

Training automatically runs a before/after benchmark and shows a comparison table.

### Visual Controls

- **Space / Enter** — pause/unpause (shows detailed player status overlay when paused)
- **Up/Down arrows** — speed up/slow down (2x increments, up to 64x)
- **Q/Escape** — quit

## Writing a Bot

Bots implement one method:

```python
from clauralux.bots.base import Bot
from clauralux.engine.actions import Action, SendUnits
from clauralux.engine.view import GameView

class MyBot(Bot):
    def decide(self, view: GameView) -> list[Action]:
        actions = []
        for sun in view.my_suns():
            if sun.garrison > 10:
                targets = view.enemy_suns() or view.neutral_suns()
                if targets:
                    target = min(targets, key=lambda s: s.garrison)
                    actions.append(SendUnits(sun.id, target.id, sun.garrison - 3))
                    self._intent = f"Attacking Sun {target.id}"
        return actions
```

Add it to `BOT_REGISTRY` in `bots/registry.py` and it appears in the GUI menu automatically.

## Project Structure

```
src/clauralux/
    engine/             # Game simulation (zero deps)
        game.py         # Tick-based engine
        config.py       # All tunable parameters
        mapgen.py       # Themed random map generation
        campaign.py     # 18-level campaign definitions
    bots/               # Bot framework + 14 strategies
        base.py         # Abstract Bot class with intent narration
        registry.py     # Central bot registry
        evolved.py      # Parameterized bot with 25 evolvable weights
    training/           # Evolutionary training system
        genome.py       # Parameter definitions and serialization
        evolution.py    # Selection, crossover, mutation, weighted fitness
        trainer.py      # Training loop with parallel eval, self-play, stagnation resets
    renderer/           # Pygame visualization
        renderer.py     # Game renderer
        commentary.py   # Sports commentary overlay with event detection
        menu.py         # Data-driven GUI menu
    runner/             # Game execution
        headless.py     # Fast bot-vs-bot
        visual.py       # Pygame display with commentary integration
        tournament.py   # Multi-game comparison
    replay/             # Game recording and playback
    cli.py              # CLI + GUI entry point
rust/                   # Rust game engine (compiled via PyO3/maturin)
tests/                  # 127 tests
```

## Development

```bash
make format     # Auto-format code with ruff
make lint       # Run ruff linter
make type       # Type check with mypy
make test       # Run test suite
make check      # Run all checks (format, lint, type, test)
```

## License

MIT — see LICENSE file for details
