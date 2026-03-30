"""Sports commentary system for visual game mode.

Detects game events, generates enthusiastic commentary text, and renders
it as an overlay on the game screen with floating annotations.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

import pygame

from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId, SunId

from .colors import get_bright_color

# Player colour names for commentary text.
_COLOUR_NAMES: dict[int, str] = {
    1: "Blue",
    2: "Red",
    3: "Green",
    4: "Yellow",
    5: "Purple",
    6: "Orange",
}


def _player_name(pid: PlayerId, bot_names: dict[PlayerId, str] | None = None) -> str:
    """Human-readable player name like 'Blue (expander)'."""
    colour = _COLOUR_NAMES.get(int(pid), f"P{pid}")
    if bot_names and pid in bot_names:
        return f"{colour} ({bot_names[pid]})"
    return colour


# ── Game Events ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GameEvent:
    """A notable event detected from game state changes."""

    tick: int
    event_type: str  # capture, upgrade, elimination, large_wave, momentum, opening, periodic
    severity: str  # minor, major, critical
    player_id: PlayerId | None = None
    sun_id: SunId | None = None
    position: tuple[float, float] | None = None
    details: dict[str, object] = field(default_factory=dict)


# ── Event Detection ─────────────────────────────────────────────────────

# Minimum ticks between events of the same type to avoid spam.
_COOLDOWNS: dict[str, int] = {
    "capture": 30,
    "upgrade": 100,
    "large_wave": 200,
    "momentum": 300,
}

_LARGE_WAVE_THRESHOLD = 15
_MOMENTUM_WINDOW = 200
_MOMENTUM_SWING = 2
_PERIODIC_INTERVAL = 500


class EventDetector:
    """Compares consecutive game states to detect notable events."""

    def __init__(self, initial_state: GameState) -> None:
        self._prev_owners: dict[SunId, PlayerId] = {
            sid: sun.owner for sid, sun in initial_state.suns.items()
        }
        self._prev_levels: dict[SunId, int] = {
            sid: sun.level for sid, sun in initial_state.suns.items()
        }
        self._prev_eliminated: set[PlayerId] = set(initial_state.eliminated)
        self._opening_done = False

        # Per-player sun count history for momentum detection.
        self._sun_count_history: list[dict[PlayerId, int]] = []

        # Last tick an event type fired, for cooldowns.
        self._last_fired: dict[str, int] = {}

        # Track large waves we've already commented on (by group identity).
        self._seen_wave_ticks: set[int] = set()

    def _on_cooldown(self, event_type: str, tick: int) -> bool:
        cooldown = _COOLDOWNS.get(event_type, 0)
        last = self._last_fired.get(event_type, -cooldown - 1)
        return (tick - last) < cooldown

    def _fire(self, event_type: str, tick: int) -> None:
        self._last_fired[event_type] = tick

    def detect(self, state: GameState) -> list[GameEvent]:
        """Detect events by comparing current state to previous snapshot."""
        events: list[GameEvent] = []
        tick = state.tick

        # Opening analysis — fires once at tick 0.
        if not self._opening_done and tick == 0:
            self._opening_done = True
            events.append(
                GameEvent(
                    tick=tick,
                    event_type="opening",
                    severity="minor",
                )
            )

        # Captures and upgrades.
        for sid, sun in state.suns.items():
            prev_owner = self._prev_owners.get(sid, NEUTRAL)
            if sun.owner != prev_owner and not self._on_cooldown("capture", tick):
                severity = "major" if prev_owner != NEUTRAL else "minor"
                events.append(
                    GameEvent(
                        tick=tick,
                        event_type="capture",
                        severity=severity,
                        player_id=sun.owner,
                        sun_id=sid,
                        position=(sun.position.x, sun.position.y),
                        details={"from_owner": int(prev_owner)},
                    )
                )
                self._fire("capture", tick)

            prev_level = self._prev_levels.get(sid, 1)
            if (
                sun.level > prev_level
                and sun.owner != NEUTRAL
                and not self._on_cooldown("upgrade", tick)
            ):
                events.append(
                    GameEvent(
                        tick=tick,
                        event_type="upgrade",
                        severity="minor",
                        player_id=sun.owner,
                        sun_id=sid,
                        position=(sun.position.x, sun.position.y),
                        details={"new_level": sun.level},
                    )
                )
                self._fire("upgrade", tick)

        # Eliminations.
        newly_eliminated = set(state.eliminated) - self._prev_eliminated
        for pid in newly_eliminated:
            events.append(
                GameEvent(
                    tick=tick,
                    event_type="elimination",
                    severity="critical",
                    player_id=pid,
                )
            )

        # Large waves.
        if not self._on_cooldown("large_wave", tick):
            for group in state.unit_groups:
                if group.count >= _LARGE_WAVE_THRESHOLD:
                    wave_key = hash((int(group.owner), group.count, tick // 50))
                    if wave_key not in self._seen_wave_ticks:
                        self._seen_wave_ticks.add(wave_key)
                        target_sun = state.suns.get(group.target_sun_id)
                        events.append(
                            GameEvent(
                                tick=tick,
                                event_type="large_wave",
                                severity="minor",
                                player_id=group.owner,
                                position=(group.position.x, group.position.y),
                                details={
                                    "count": group.count,
                                    "target_sun_id": int(group.target_sun_id)
                                    if target_sun
                                    else None,
                                },
                            )
                        )
                        self._fire("large_wave", tick)
                        break  # one wave comment per tick max

        # Momentum shift — track sun counts over time.
        sun_counts: dict[PlayerId, int] = Counter()
        for sun in state.suns.values():
            if sun.owner != NEUTRAL:
                sun_counts[sun.owner] += 1
        self._sun_count_history.append(dict(sun_counts))
        if len(self._sun_count_history) > _MOMENTUM_WINDOW:
            self._sun_count_history.pop(0)

        if len(self._sun_count_history) >= _MOMENTUM_WINDOW and not self._on_cooldown(
            "momentum", tick
        ):
            old_counts = self._sun_count_history[0]
            for pid, current in sun_counts.items():
                old = old_counts.get(pid, 0)
                if current - old >= _MOMENTUM_SWING:
                    events.append(
                        GameEvent(
                            tick=tick,
                            event_type="momentum",
                            severity="major",
                            player_id=pid,
                            details={"gained": current - old, "total": current},
                        )
                    )
                    self._fire("momentum", tick)
                    break

        # Periodic updates.
        if tick > 0 and tick % _PERIODIC_INTERVAL == 0:
            events.append(
                GameEvent(
                    tick=tick,
                    event_type="periodic",
                    severity="minor",
                )
            )

        # Update tracked state for next call.
        self._prev_owners = {sid: sun.owner for sid, sun in state.suns.items()}
        self._prev_levels = {sid: sun.level for sid, sun in state.suns.items()}
        self._prev_eliminated = set(state.eliminated)

        return events


# ── Commentary Text Generation ──────────────────────────────────────────

_OPENING = [
    "Welcome to Clauralux! {num_players} players, {neutral_suns} suns up for grabs!",
    "HERE WE GO! {num_players} players, {neutral_suns} neutral suns to conquer!",
    "The battlefield is set! {num_suns} suns, {neutral_suns} unclaimed. Who strikes first?",
]

_CAPTURE_NEUTRAL = [
    "{player} grabs sun #{sun_id}! Smart expansion!",
    "{player} moves into sun #{sun_id} — territory secured!",
    "Sun #{sun_id} falls to {player}! That's {total_suns} suns now!",
    "{player} claims sun #{sun_id}! Growing that empire!",
]

_CAPTURE_HOSTILE = [
    "HOSTILE TAKEOVER! {player} seizes sun #{sun_id} from {victim}!",
    "WHAT A PLAY! {player} rips sun #{sun_id} away from {victim}!",
    "Sun #{sun_id} changes hands! {player} takes it from {victim}!",
    "CAPTURED! {player} storms {victim}'s sun #{sun_id}!",
]

_UPGRADE = [
    "{player} upgrades sun #{sun_id} to level {level}! More production incoming!",
    "Sun #{sun_id} levels up for {player}! That economy is growing!",
    "{player} invests in sun #{sun_id} — now level {level}!",
]

_ELIMINATION = [
    "AND IT'S OVER FOR {victim}! ELIMINATED! {remaining} player(s) remain!",
    "{victim} IS OUT! What a collapse! Down to {remaining}!",
    "ELIMINATED! {victim} falls! {remaining} player(s) left standing!",
]

_LARGE_WAVE = [
    "{player} sends a MASSIVE wave of {count} units! Here it comes!",
    "HUGE attack from {player}! {count} units on the move!",
    "That's {count} units from {player} — someone is in trouble!",
]

_MOMENTUM = [
    "The tide is turning! {player} has grabbed {gained} suns recently — {total} total!",
    "{player} is on a ROLL! Up to {total} suns! Can anyone stop them?",
    "MOMENTUM SHIFT! {player} surging ahead with {total} suns!",
]

_PERIODIC = [
    "Tick {tick}: {leader} leads with {leader_suns} suns! {summary}",
    "Status check at tick {tick} — {leader} out front with {leader_suns} suns! {summary}",
    "At tick {tick}, {leader} holds {leader_suns} suns. {summary}",
]

_INTENT_PHRASES = [
    '{player}: "{intent}"',
    '{player} says: "{intent}"',
]


class CommentaryGenerator:
    """Generates commentary text from game events using template pools."""

    def __init__(
        self,
        bot_names: dict[PlayerId, str] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._bot_names = bot_names or {}
        self._rng = rng or random.Random()

    def _name(self, pid: PlayerId) -> str:
        return _player_name(pid, self._bot_names)

    def generate(
        self,
        event: GameEvent,
        state: GameState,
        bot_intents: dict[PlayerId, str] | None = None,
    ) -> str:
        """Generate commentary text for an event."""
        if event.event_type == "opening":
            return self._opening(state)
        elif event.event_type == "capture":
            return self._capture(event, state)
        elif event.event_type == "upgrade":
            return self._upgrade(event)
        elif event.event_type == "elimination":
            return self._elimination(event, state)
        elif event.event_type == "large_wave":
            return self._large_wave(event)
        elif event.event_type == "momentum":
            return self._momentum(event)
        elif event.event_type == "periodic":
            return self._periodic(event, state, bot_intents)
        return ""

    def _opening(self, state: GameState) -> str:
        num_players = len(state.players)
        num_suns = len(state.suns)
        neutral_suns = sum(1 for s in state.suns.values() if s.owner == NEUTRAL)
        template = self._rng.choice(_OPENING)
        return template.format(
            num_players=num_players,
            num_suns=num_suns,
            neutral_suns=neutral_suns,
        )

    def _capture(self, event: GameEvent, state: GameState) -> str:
        assert event.player_id is not None
        from_owner = PlayerId(event.details.get("from_owner", 0))  # type: ignore[arg-type]
        player = self._name(event.player_id)

        if from_owner == NEUTRAL:
            total_suns = sum(1 for s in state.suns.values() if s.owner == event.player_id)
            template = self._rng.choice(_CAPTURE_NEUTRAL)
            return template.format(
                player=player,
                sun_id=event.sun_id,
                total_suns=total_suns,
            )
        else:
            victim = self._name(from_owner)
            template = self._rng.choice(_CAPTURE_HOSTILE)
            return template.format(
                player=player,
                victim=victim,
                sun_id=event.sun_id,
            )

    def _upgrade(self, event: GameEvent) -> str:
        assert event.player_id is not None
        template = self._rng.choice(_UPGRADE)
        return template.format(
            player=self._name(event.player_id),
            sun_id=event.sun_id,
            level=event.details.get("new_level", "?"),
        )

    def _elimination(self, event: GameEvent, state: GameState) -> str:
        assert event.player_id is not None
        remaining = len(state.players) - len(state.eliminated)
        template = self._rng.choice(_ELIMINATION)
        return template.format(
            victim=self._name(event.player_id),
            remaining=remaining,
        )

    def _large_wave(self, event: GameEvent) -> str:
        assert event.player_id is not None
        template = self._rng.choice(_LARGE_WAVE)
        return template.format(
            player=self._name(event.player_id),
            count=event.details.get("count", "?"),
        )

    def _momentum(self, event: GameEvent) -> str:
        assert event.player_id is not None
        template = self._rng.choice(_MOMENTUM)
        return template.format(
            player=self._name(event.player_id),
            gained=event.details.get("gained", "?"),
            total=event.details.get("total", "?"),
        )

    def _periodic(
        self,
        event: GameEvent,
        state: GameState,
        bot_intents: dict[PlayerId, str] | None = None,
    ) -> str:
        if state.winner == NEUTRAL:
            return f"It's a DRAW at tick {event.tick}! Neither player could finish the other!"

        # Find leader by sun count.
        sun_counts: dict[PlayerId, int] = Counter()
        for sun in state.suns.values():
            if sun.owner != NEUTRAL:
                sun_counts[sun.owner] += 1

        if not sun_counts:
            return f"Tick {event.tick}: Nobody owns anything yet!"

        leader_pid = max(sun_counts, key=lambda p: sun_counts[p])
        leader = self._name(leader_pid)
        leader_suns = sun_counts[leader_pid]

        # Build a summary from bot intents if available.
        summary = ""
        if bot_intents:
            active = [
                (pid, intent)
                for pid, intent in bot_intents.items()
                if pid not in state.eliminated and intent
            ]
            if active:
                pid, intent = self._rng.choice(active)
                template = self._rng.choice(_INTENT_PHRASES)
                summary = template.format(
                    player=self._name(pid),
                    intent=intent,
                )

        template = self._rng.choice(_PERIODIC)
        return template.format(
            tick=event.tick,
            leader=leader,
            leader_suns=leader_suns,
            summary=summary,
        )


# ── Overlay Rendering ───────────────────────────────────────────────────

_BANNER_DURATION = 150  # frames (~3 seconds at 50fps)
_BANNER_FADE_START = 30  # start fading in last N frames
_FLOAT_DURATION = 40  # frames (~0.8 seconds)
_FLOAT_DRIFT = 0.5  # pixels per frame upward


@dataclass(slots=True)
class FloatingText:
    """A piece of text that floats and fades near an event location."""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    frames_remaining: int = _FLOAT_DURATION
    max_frames: int = _FLOAT_DURATION


class CommentaryOverlay:
    """Renders commentary text as a screen overlay."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height

        self._banner_font = pygame.font.SysFont("monospace", 16, bold=True)
        self._float_font = pygame.font.SysFont("monospace", 13, bold=True)

        self._banner_text = ""
        self._banner_frames = 0

        self._floating_texts: list[FloatingText] = []

    def set_banner(self, text: str) -> None:
        """Set the main commentary banner text."""
        self._banner_text = text
        self._banner_frames = _BANNER_DURATION

    def add_floating_text(self, text: str, x: float, y: float, color: tuple[int, int, int]) -> None:
        """Add floating text near an event position (screen coordinates)."""
        self._floating_texts.append(FloatingText(text, x, y - 30, color))

    def draw(self, screen: pygame.Surface) -> None:
        """Render banner and floating texts onto the screen."""
        self._draw_banner(screen)
        self._draw_floating(screen)

    def _draw_banner(self, screen: pygame.Surface) -> None:
        if self._banner_frames <= 0 or not self._banner_text:
            return

        # Calculate alpha (fade in last N frames).
        if self._banner_frames <= _BANNER_FADE_START:
            alpha = int(255 * self._banner_frames / _BANNER_FADE_START)
        else:
            alpha = 255

        # Render text.
        text_surface = self._banner_font.render(self._banner_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(centerx=self._screen_width // 2, y=8)

        # Dark backdrop.
        padding = 8
        backdrop = pygame.Surface(
            (text_rect.width + padding * 2, text_rect.height + padding),
            pygame.SRCALPHA,
        )
        backdrop.fill((0, 0, 0, min(alpha, 180)))
        screen.blit(backdrop, (text_rect.x - padding, text_rect.y - padding // 2))

        # Text with alpha.
        text_surface.set_alpha(alpha)
        screen.blit(text_surface, text_rect)

        self._banner_frames -= 1

    def _draw_floating(self, screen: pygame.Surface) -> None:
        alive: list[FloatingText] = []
        for ft in self._floating_texts:
            if ft.frames_remaining <= 0:
                continue

            alpha = int(255 * ft.frames_remaining / ft.max_frames)
            text_surface = self._float_font.render(ft.text, True, ft.color)
            text_surface.set_alpha(alpha)
            rect = text_surface.get_rect(centerx=int(ft.x), centery=int(ft.y))
            screen.blit(text_surface, rect)

            ft.y -= _FLOAT_DRIFT
            ft.frames_remaining -= 1
            alive.append(ft)

        self._floating_texts = alive


# ── Commentary System Facade ────────────────────────────────────────────

# Short labels for floating text annotations near events.
_FLOAT_LABELS: dict[str, list[str]] = {
    "capture": ["CAPTURED!", "TAKEN!", "SEIZED!"],
    "elimination": ["ELIMINATED!", "OUT!", "FINISHED!"],
    "upgrade": ["UPGRADED!", "LEVEL UP!"],
}


class CommentarySystem:
    """Top-level facade: detects events, generates commentary, renders overlay.

    Used by VisualRunner. Call update() each tick, draw() each frame.
    """

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bot_names: dict[PlayerId, str] | None = None,
        screen_width: int = 1080,
        screen_height: int = 980,
        map_to_screen: Callable[[float, float], tuple[int, int]] | None = None,
        enabled: bool = True,
        pause_on_events: bool = False,
    ) -> None:
        self._enabled = enabled
        self._pause_on_events = pause_on_events
        self._map_to_screen = map_to_screen or (lambda x, y: (int(x), int(y)))

        self._detector = EventDetector(initial_state)
        self._generator = CommentaryGenerator(bot_names)
        self._overlay = CommentaryOverlay(screen_width, screen_height)

        self._pause_requested = False
        self._pending_pause_text = ""
        self._bot_names = bot_names or {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def pause_on_events(self) -> bool:
        return self._pause_on_events

    @pause_on_events.setter
    def pause_on_events(self, value: bool) -> None:
        self._pause_on_events = value

    def update(
        self,
        state: GameState,
        bot_intents: dict[PlayerId, str] | None = None,
    ) -> bool:
        """Process one tick. Returns True if a pause is requested."""
        if not self._enabled:
            return False

        events = self._detector.detect(state)
        if not events:
            return False

        # Pick the highest-severity event for the banner.
        severity_order = {"critical": 3, "major": 2, "minor": 1}
        best_event = max(events, key=lambda e: severity_order.get(e.severity, 0))
        text = self._generator.generate(best_event, state, bot_intents)
        if text:
            self._overlay.set_banner(text)

        # Add floating text for position-based events.
        for event in events:
            if event.position is not None:
                sx, sy = self._map_to_screen(event.position[0], event.position[1])
                labels = _FLOAT_LABELS.get(event.event_type)
                if labels:
                    label = random.choice(labels)
                    pid = event.player_id or PlayerId(0)
                    color = get_bright_color(pid)
                    self._overlay.add_floating_text(label, float(sx), float(sy), color)

        # Check if we should pause.
        if self._pause_on_events and best_event.severity in ("major", "critical"):
            self._pause_requested = True
            self._pending_pause_text = text
            return True

        return False

    def draw(self, screen: pygame.Surface) -> None:
        """Render the commentary overlay onto the screen."""
        if self._enabled:
            self._overlay.draw(screen)

    def consume_pause(self) -> tuple[bool, str]:
        """Check and clear the pause request. Returns (was_paused, text)."""
        was = self._pause_requested
        text = self._pending_pause_text
        self._pause_requested = False
        self._pending_pause_text = ""
        return was, text
