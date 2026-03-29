# Improvement Plans

Three plans for making the evolved bot training produce genuinely interesting strategies, written March 2026.

## Recommended Order

1. **[Bot Diversity](plan-bot-diversity.md)** — 5 new bot archetypes (Coordinator, Economic, Reactive, Baiter, Swarm). Do this first. The current 7 hand-crafted bots all play variations of "accumulate then attack", so the evolved bot's defensive and coordination parameters have no selection pressure. New archetypes change what the evolved bot *must* learn.

2. **[Training Improvements](plan-training-improvements.md)** — Self-play, more map types, richer fitness signal, seed rotation. Do this after the new bots exist and are registered in the training opponent pool. These changes make training more robust, but they're only worth doing once the opponent pool is diverse enough to push the evolved bot somewhere interesting.

3. **[Replay System](plan-replay-system.md)** — Record and play back games. Do this last. It's a diagnostic tool — most valuable once the bot is learning from richer training and you want to understand *why* it makes specific decisions.

## Dependencies and Caveats

- A Rust refactor of the engine may be in progress or complete by the time you read this. The plans are written against the Python bot/runner/training interfaces, not engine internals. If `GameConfig`, `Position`, or `GameState` are now Rust types exposed via PyO3, the replay plan's serialisation approach (JSON of Python dataclasses) will need adaptation — you'll need to handle serialisation at the Rust/Python boundary.

- The bot diversity plan feeds directly into the training plan. New bots should be added to `OPPONENT_BOTS` in `trainer.py` (or whatever the training opponent list is called after refactoring).

- None of the plans specify tests in detail. Each new bot should have unit tests following the pattern of existing bot tests. The replay system needs round-trip tests (record → serialise → deserialise → playback produces identical game state). Training changes need tests that verify fitness scoring and seed variation.

## Context

These plans came out of an honest review of what's limiting the project. The architecture and tooling are solid. The bottleneck is that the evolved bot trains against a narrow, homogeneous opponent pool on a small set of maps, producing threshold-tuned heuristics rather than emergent strategy. These three plans address that from different angles.
