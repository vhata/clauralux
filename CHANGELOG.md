# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
