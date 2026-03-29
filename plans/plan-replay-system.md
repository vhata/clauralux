# Plan: Replay System

## Why

The evolved bot's training runs produce win/loss results but no way to inspect *what happened*. When a generation regresses or a bot makes bizarre decisions, you can't go back and look. Replays let you debug training, compare generations, and spot strategy gaps — all cheaply, since the engine is already deterministic.

## Design

### Recording

Record the minimum needed to reproduce a game:

1. **Game config** — serialised `GameConfig` fields as a dict
2. **Initial state** — full `GameState` snapshot (sun positions, owners, garrisons, players)
3. **Action log** — list of `(tick, player_id, actions)` entries, only on decision ticks
4. **Metadata** — bot names/types per player, game result, timestamp, generation number (if training)

Actions are only submitted every `config.decision_interval` ticks, so the log is sparse. A typical 3000-tick game with 5-tick decision interval = ~600 decision points × N players. Small.

### Storage Format

JSON lines or a single JSON file per game. Keep it human-readable for now — performance isn't the bottleneck. Something like:

```json
{
  "version": 1,
  "timestamp": "2026-03-29T12:00:00Z",
  "config": { "unit_speed": 2.0, ... },
  "initial_state": { "suns": [...], "players": [...] },
  "bots": { "1": "EvolvedBot", "2": "ExpanderBot" },
  "actions": [
    { "tick": 0, "player": 1, "actions": [{"type": "send_units", "source": 1, "target": 3, "count": 5}] },
    { "tick": 0, "player": 2, "actions": [] },
    { "tick": 5, "player": 1, "actions": [{"type": "upgrade_sun", "sun": 1}] }
  ],
  "result": { "winner": 1, "ticks": 2847, "is_draw": false }
}
```

Store replays in `~/.config/clauralux/replays/` or a `replays/` directory in the project (gitignored).

### Playback

Create a `ReplayBot` that implements `Bot` and returns pre-recorded actions:

```python
class ReplayBot(Bot):
    def __init__(self, action_log: dict[Tick, list[Action]]) -> None:
        super().__init__()
        self._action_log = action_log

    def decide(self, view: GameView) -> list[Action]:
        return self._action_log.get(view.tick, [])
```

Feed `ReplayBot` instances into the existing `VisualRunner`. No new renderer needed. The intent display can show "Replay" or the original bot type name.

### Recording Integration

Two insertion points:

1. **HeadlessRunner** — add an optional `record=True` flag. After each `apply_actions` call, append to the action log. After `run()` completes, write the replay file. This is the training path.
2. **VisualRunner** — same approach, always record (or flag-controlled). This is the watch path.

Alternatively, build a `GameRecorder` helper class that wraps the action-capture logic so both runners can use it without duplication.

### CLI Integration

Add a `replay` subcommand:

```
clauralux replay path/to/replay.json
```

Opens the visual runner with `ReplayBot` instances. Supports the same speed controls and pause as normal visual mode.

### Training Integration

The trainer can optionally save replays for:
- Every game of the best candidate each generation
- Games where the evolved bot loses (most useful for debugging)
- A configurable sample rate

This keeps storage bounded while capturing the interesting cases.

## Implementation Order

1. Action serialisation/deserialisation for `SendUnits` and `UpgradeSun`
2. `GameState` and `GameConfig` serialisation
3. `GameRecorder` class (captures actions during a game)
4. `ReplayBot` class
5. Integrate recording into `HeadlessRunner`
6. Replay file writer
7. Replay file loader + `replay` CLI subcommand
8. Integrate recording into `VisualRunner`
9. Training integration (selective replay saving)

## Open Questions

- Should `GameConfig` and `Position` serialisation live in the engine layer or in a separate serialisation module? They come from the compiled Rust module, so they may need special handling.
- Replay file naming convention — timestamp-based? Include bot names? Generation number?
- Compression? Probably not needed yet, but gzip is trivial to add later if replay dirs get large.
