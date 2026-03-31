"""Records game actions for replay.

Captures the minimum needed to reproduce a game: config, initial state,
and action log. The engine is deterministic, so replaying the same
actions on the same initial state produces identical results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState, Sun
from clauralux.engine.types import PlayerId


@dataclass
class ActionEntry:
    """A single decision tick's actions for one player."""

    tick: int
    player_id: int
    actions: list[dict[str, int]]


@dataclass
class ReplayData:
    """All data needed to replay a game."""

    version: int = 1
    timestamp: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    initial_state: dict[str, Any] = field(default_factory=dict)
    bot_names: dict[str, str] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)


class GameRecorder:
    """Captures actions during a game for later replay."""

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bot_names: dict[PlayerId, str] | None = None,
    ) -> None:
        self._config_data = _serialize_config(config)
        self._state_data = _serialize_state(initial_state)
        self._bot_names = {str(int(pid)): name for pid, name in (bot_names or {}).items()}
        self._action_log: list[dict[str, Any]] = []

    def record_actions(self, tick: int, player_id: PlayerId, actions: list[Action]) -> None:
        """Record one player's actions for a tick."""
        if not actions:
            return
        serialized = [_serialize_action(a) for a in actions]
        self._action_log.append(
            {
                "tick": tick,
                "player": int(player_id),
                "actions": serialized,
            }
        )

    def finish(
        self,
        winner: PlayerId | None,
        ticks: int,
        is_draw: bool,
    ) -> ReplayData:
        """Finalize the recording with the game result."""
        return ReplayData(
            version=1,
            timestamp=datetime.now(UTC).isoformat(),
            config=self._config_data,
            initial_state=self._state_data,
            bot_names=self._bot_names,
            actions=self._action_log,
            result={
                "winner": int(winner) if winner is not None else None,
                "ticks": ticks,
                "is_draw": is_draw,
            },
        )


def save_replay(data: ReplayData, path: str | Path) -> None:
    """Save a replay to a JSON file. Use .json.gz extension for gzip compression."""
    import gzip

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(_replay_to_dict(data), indent=2) + "\n"
    if p.suffix == ".gz" or str(p).endswith(".json.gz"):
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.write(content)
    else:
        p.write_text(content)


def load_replay(path: str | Path) -> ReplayData:
    """Load a replay from a JSON file. Handles both plain and gzipped files."""
    import gzip

    p = Path(path)
    if p.suffix == ".gz" or str(p).endswith(".json.gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            raw = json.loads(f.read())
    else:
        raw = json.loads(p.read_text())
    return ReplayData(
        version=raw.get("version", 1),
        timestamp=raw.get("timestamp", ""),
        config=raw.get("config", {}),
        initial_state=raw.get("initial_state", {}),
        bot_names=raw.get("bot_names", {}),
        actions=raw.get("actions", []),
        result=raw.get("result", {}),
    )


def replay_to_game(
    data: ReplayData,
) -> tuple[GameConfig, GameState, dict[int, list[tuple[int, list[Action]]]]]:
    """Convert replay data back into a GameConfig, GameState, and action schedule.

    Returns (config, initial_state, action_schedule) where action_schedule maps
    player_id to a list of (tick, actions) pairs.
    """
    config = _deserialize_config(data.config)
    state = _deserialize_state(data.initial_state)

    # Build action schedule: player_id -> [(tick, actions), ...]
    schedule: dict[int, list[tuple[int, list[Action]]]] = {}
    for entry in data.actions:
        tick = int(entry["tick"])
        player = int(entry["player"])
        actions = [_deserialize_action(a) for a in entry["actions"]]
        if player not in schedule:
            schedule[player] = []
        schedule[player].append((tick, actions))

    return config, state, schedule


# ── Serialization helpers ─────────────────────────────────────────────


def _serialize_config(config: GameConfig) -> dict[str, Any]:
    return {
        "map_width": config.map_width,
        "map_height": config.map_height,
        "production_interval": config.production_interval,
        "production_per_level": config.production_per_level,
        "max_sun_level": config.max_sun_level,
        "upgrade_costs": list(config.upgrade_costs),
        "capture_level_reset": config.capture_level_reset,
        "unit_speed": config.unit_speed,
        "attack_ratio": config.attack_ratio,
        "decision_interval": config.decision_interval,
        "max_ticks": config.max_ticks,
        "ticks_per_second": config.ticks_per_second,
        "default_neutral_garrison": config.default_neutral_garrison,
        "default_player_garrison": config.default_player_garrison,
        "seed": config.seed,
    }


def _deserialize_config(data: dict[str, Any]) -> GameConfig:
    return GameConfig(**data)


def _serialize_state(state: GameState) -> dict[str, Any]:
    suns = []
    for sun in state.suns.values():
        suns.append(
            {
                "id": sun.id,
                "x": sun.position.x,
                "y": sun.position.y,
                "owner": sun.owner,
                "level": sun.level,
                "garrison": sun.garrison,
            }
        )
    return {
        "suns": suns,
        "players": list(state.players),
    }


def _deserialize_state(data: dict[str, Any]) -> GameState:
    from clauralux.engine.types import Position, SunId

    suns_data = data.get("suns", [])
    suns = {}
    for s in suns_data:
        sun_id = SunId(int(s["id"]))
        suns[sun_id] = Sun(
            id=sun_id,
            position=Position(float(s["x"]), float(s["y"])),
            owner=PlayerId(int(s["owner"])),
            level=int(s["level"]),
            garrison=float(s["garrison"]),
        )
    players = [PlayerId(int(p)) for p in data.get("players", [])]
    return GameState(suns=suns, players=players)


def _serialize_action(action: Action) -> dict[str, int]:
    if isinstance(action, SendUnits):
        return {
            "type": 0,
            "source": action.source_sun_id,
            "target": action.target_sun_id,
            "count": action.count,
        }
    elif isinstance(action, UpgradeSun):
        return {"type": 1, "sun": action.sun_id}
    return {}


def _deserialize_action(data: Any) -> Action:
    d = data
    if d["type"] == 0:
        return SendUnits(
            source_sun_id=d["source"],
            target_sun_id=d["target"],
            count=d["count"],
        )
    else:
        return UpgradeSun(sun_id=d["sun"])


def _replay_to_dict(data: ReplayData) -> dict[str, Any]:
    return {
        "version": data.version,
        "timestamp": data.timestamp,
        "config": data.config,
        "initial_state": data.initial_state,
        "bot_names": data.bot_names,
        "actions": data.actions,
        "result": data.result,
    }
