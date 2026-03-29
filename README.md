# Clauralux

An Auralux clone built for bot strategy development. The game engine is completely decoupled from rendering — write bots, pit them against each other headlessly at full speed, or watch them fight in a pygame window.

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
- **4 built-in bots** — passive, random, aggressive, expander (each with strategic intent narration)
- **Themed random maps** — strategic, rush, chokepoint, swarm
- **18-level campaign** — gradual difficulty progression from passive to dual-aggressive enemies
- **Tournament system** — run N games and compare bot win rates
- **GUI menu** — configure and launch games without touching the CLI
- **Visual renderer** — pygame-ce with pulsing suns, unit swarms, trajectory lines, capture flashes

## Prerequisites

- Python 3.12+
- uv (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Quickstart

```bash
uv venv .venv
uv sync --group dev --extra visual
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
uv run clauralux watch --bot aggressive --bot expander

# Watch a random rush map
uv run clauralux watch --map random:rush --bot aggressive --bot expander

# Run headless (fast, no display)
uv run clauralux headless --bot expander --bot aggressive

# Tournament: 100 games, compare win rates
uv run clauralux tournament --bot aggressive --bot expander --games 100

# Campaign: play through 18 levels
uv run clauralux campaign --bot expander

# Campaign: start from level 10, headless
uv run clauralux campaign --bot aggressive --level 10 --headless
```

### Visual Controls

- **Space** — pause/unpause
- **Up/Down arrows** — speed up/slow down (2x increments)
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

Add it to `BOT_REGISTRY` in `cli.py` and it appears in the GUI menu automatically.

## Project Structure

```
src/clauralux/
    engine/         # Game simulation (zero deps)
        game.py     # Tick-based engine
        config.py   # All tunable parameters
        mapgen.py   # Themed random map generation
        campaign.py # 18-level campaign definitions
    bots/           # Bot framework + built-in strategies
        base.py     # Abstract Bot class with intent narration
    renderer/       # Pygame visualization
        renderer.py # Game renderer
        menu.py     # Data-driven GUI menu
    runner/         # Game execution
        headless.py # Fast bot-vs-bot
        visual.py   # Pygame display
        tournament.py # Multi-game comparison
    cli.py          # CLI + GUI entry point
tests/              # 57 tests, ~60% coverage
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
