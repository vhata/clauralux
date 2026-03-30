import random

import pygame
import pytest

from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState, Sun
from clauralux.engine.types import NEUTRAL, PlayerId, Position, SunId, Tick
from clauralux.renderer.commentary import (
    CommentaryGenerator,
    CommentarySystem,
    EventDetector,
    GameEvent,
)

_pygame_available = False
try:
    pygame.init()
    _pygame_available = True
except Exception:
    pass

P1 = PlayerId(1)
P2 = PlayerId(2)


def _make_state(
    owners: dict[int, int] | None = None,
    levels: dict[int, int] | None = None,
    tick: int = 0,
    eliminated: set[PlayerId] | None = None,
) -> GameState:
    """Build a simple 3-sun state for testing."""
    owners = owners or {0: int(P1), 1: int(P2), 2: int(NEUTRAL)}
    levels = levels or {}
    suns = {}
    for sid_int, owner_int in owners.items():
        suns[SunId(sid_int)] = Sun(
            SunId(sid_int),
            Position(float(sid_int * 100), 0.0),
            owner=PlayerId(owner_int),
            level=levels.get(sid_int, 1),
            garrison=10.0,
        )
    state = GameState(suns=suns, players=[P1, P2], tick=Tick(tick), eliminated=eliminated or set())
    return state


class TestEventDetector:
    def test_opening_fires_at_tick_zero(self) -> None:
        state = _make_state(tick=0)
        detector = EventDetector(state)
        events = detector.detect(state)
        opening = [e for e in events if e.event_type == "opening"]
        assert len(opening) == 1

    def test_opening_fires_only_once(self) -> None:
        state = _make_state(tick=0)
        detector = EventDetector(state)
        detector.detect(state)
        events = detector.detect(state)
        opening = [e for e in events if e.event_type == "opening"]
        assert len(opening) == 0

    def test_capture_from_neutral(self) -> None:
        initial = _make_state(owners={0: int(P1), 1: int(P2), 2: int(NEUTRAL)})
        detector = EventDetector(initial)

        # Sun 2 captured by P1.
        after = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        events = detector.detect(after)
        captures = [e for e in events if e.event_type == "capture"]
        assert len(captures) == 1
        assert captures[0].severity == "minor"
        assert captures[0].player_id == P1

    def test_capture_from_player_is_major(self) -> None:
        initial = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P2)})
        detector = EventDetector(initial)

        # Sun 2 captured by P1 from P2.
        after = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        events = detector.detect(after)
        captures = [e for e in events if e.event_type == "capture"]
        assert len(captures) == 1
        assert captures[0].severity == "major"

    def test_capture_cooldown(self) -> None:
        initial = _make_state()
        detector = EventDetector(initial)

        # First capture at tick 1.
        state1 = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        events1 = detector.detect(state1)
        assert any(e.event_type == "capture" for e in events1)

        # Another capture at tick 2 — should be on cooldown.
        state2 = _make_state(owners={0: int(P1), 1: int(P1), 2: int(P1)}, tick=2)
        events2 = detector.detect(state2)
        assert not any(e.event_type == "capture" for e in events2)

    def test_elimination_detected(self) -> None:
        initial = _make_state()
        detector = EventDetector(initial)

        after = _make_state(tick=1, eliminated={P2})
        events = detector.detect(after)
        elims = [e for e in events if e.event_type == "elimination"]
        assert len(elims) == 1
        assert elims[0].player_id == P2
        assert elims[0].severity == "critical"

    def test_periodic_at_interval(self) -> None:
        initial = _make_state(tick=0)
        detector = EventDetector(initial)
        detector.detect(initial)  # tick 0 — opening, not periodic

        state = _make_state(tick=500)
        events = detector.detect(state)
        periodic = [e for e in events if e.event_type == "periodic"]
        assert len(periodic) == 1

    def test_upgrade_detected(self) -> None:
        initial = _make_state(levels={0: 1, 1: 1, 2: 1})
        detector = EventDetector(initial)

        after = _make_state(levels={0: 2, 1: 1, 2: 1}, tick=1)
        events = detector.detect(after)
        upgrades = [e for e in events if e.event_type == "upgrade"]
        assert len(upgrades) == 1
        assert upgrades[0].player_id == P1


class TestCommentaryGenerator:
    def test_generate_opening(self) -> None:
        state = _make_state(tick=0)
        gen = CommentaryGenerator(
            bot_names={P1: "evolved", P2: "aggressive"},
            rng=random.Random(42),
        )
        event = GameEvent(tick=0, event_type="opening", severity="minor")
        text = gen.generate(event, state)
        assert text
        # Should mention number of suns or players.
        assert any(word in text for word in ["3", "2", "1", "suns", "players"])

    def test_generate_capture_includes_player_name(self) -> None:
        state = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        gen = CommentaryGenerator(
            bot_names={P1: "evolved", P2: "aggressive"},
            rng=random.Random(42),
        )
        event = GameEvent(
            tick=1,
            event_type="capture",
            severity="minor",
            player_id=P1,
            sun_id=SunId(2),
            details={"from_owner": 0},
        )
        text = gen.generate(event, state)
        assert "Blue" in text

    def test_generate_elimination(self) -> None:
        state = _make_state(tick=100, eliminated={P2})
        gen = CommentaryGenerator(rng=random.Random(42))
        event = GameEvent(
            tick=100,
            event_type="elimination",
            severity="critical",
            player_id=P2,
        )
        text = gen.generate(event, state)
        assert "Red" in text

    def test_periodic_with_intents(self) -> None:
        state = _make_state(tick=500)
        gen = CommentaryGenerator(
            bot_names={P1: "evolved", P2: "aggressive"},
            rng=random.Random(42),
        )
        event = GameEvent(tick=500, event_type="periodic", severity="minor")
        intents = {P1: "Upgrading Sun 0", P2: "Attacking weakest target"}
        text = gen.generate(event, state, bot_intents=intents)
        assert text  # should produce something


@pytest.mark.skipif(not _pygame_available, reason="pygame not initialized")
class TestCommentarySystem:
    def test_disabled_returns_false(self) -> None:
        state = _make_state(tick=0)
        system = CommentarySystem(
            config=GameConfig(),
            initial_state=state,
            enabled=False,
        )
        assert system.update(state) is False

    def test_pause_on_events(self) -> None:
        initial = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P2)})
        system = CommentarySystem(
            config=GameConfig(),
            initial_state=initial,
            enabled=True,
            pause_on_events=True,
        )
        # Hostile capture — should trigger pause.
        after = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        result = system.update(after)
        assert result is True

    def test_consume_pause_clears_flag(self) -> None:
        initial = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P2)})
        system = CommentarySystem(
            config=GameConfig(),
            initial_state=initial,
            enabled=True,
            pause_on_events=True,
        )
        after = _make_state(owners={0: int(P1), 1: int(P2), 2: int(P1)}, tick=1)
        system.update(after)
        was_paused, text = system.consume_pause()
        assert was_paused is True
        assert text

        # Second consume should be clear.
        was_paused2, _ = system.consume_pause()
        assert was_paused2 is False
