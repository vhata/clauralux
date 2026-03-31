# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Quick play mode (`./clauralux play`) with guided difficulty and map selection for beginners
- Human player with mouse controls (click to select, click to send, Shift for half, right-click deselect)
- Neural net bot (MLP: 12 inputs → 32 hidden → 29 outputs, 1373 evolvable weights) with adaptive strategy and action priority ordering
- Phase-based evolved bot (3 game phases x 25 params + 2 transition thresholds = 77 params)
- Sports commentary overlay with event detection, floating text annotations, and optional pause-on-big-moments
- Benchmark command: scorecard of evolved/neural bot win rates against all opponents
- Megatrain command: intensive 3-phase training with automatic before/after benchmarking
- Self-play training mode (--self-play flag)
- Stagnation reset: sigma and population injection when fitness plateaus
- Opponent difficulty weighting in fitness evaluation
- 12 themed fun maps: grid, fortress, bridge, ring, corridor, archipelago, spiral, diamond (2p) + crossroads, web (3p) + arena, kingdoms (4p)
- 24-level campaign across 4 acts, teaching mechanics and introducing each bot type
- Replay system: record, save, load, and play back games
- ./clauralux launcher script for easy invocation
- 5 new bot archetypes: SwarmBot, CoordinatorBot, ReactiveBot, EconomicBot, BaiterBot
- Central bot registry — new bots automatically appear in CLI, menu, and training
- Noisy opponent wrapper for training diversity (randomly drops 10% of actions)

### Improved
- README: added standard map descriptions (simple, triangle, cross, pentagon, hex)
- README: explained bot `_intent` property and its role in sports commentary
- README: clarified pygame-ce as optional dependency, separated dev setup from quickstart

### Changed
- CLI refactored from argparse to click with proper subcommands
- Training defaults increased: population 80, generations 200, games/eval 40
- Hall of fame saved every 5 generations (was 10)
- Removed dead retreat_threshold parameter, tightened act_interval range
- Training now uses all 4 map flavours (strategic, rush, chokepoint, swarm)
- Richer fitness signal: rewards fast wins and territorial control, not just win/loss
- Training opponent pool now includes all 12 non-passive, non-evolved bots
- Evolved bot: parameterized heuristic bot with 26 evolvable parameters
- Evolutionary training harness (`clauralux train`) with parallel fitness evaluation
- `--from-scratch` flag for training from a clean slate
- Genome serialization (JSON) for saving/loading trained weights
- Bot strategy descriptions shown in GUI menu when selecting bots
- Bot type names displayed in game HUD (e.g. "P1 (evolved)")
- Detailed status overlay when pausing a game (Space key)
- Menu scrolling when options overflow the screen
- Settings persistence across sessions (`~/.config/clauralux/settings.json`)
- Rust game engine via PyO3 — ~10x faster training (0.4s/gen vs 5s/gen)
- Initial project setup
