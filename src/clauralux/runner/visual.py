from __future__ import annotations

from collections.abc import Mapping

import pygame

from clauralux.bots.base import Bot
from clauralux.bots.human import HumanBot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId, SunId
from clauralux.renderer.commentary import CommentarySystem
from clauralux.renderer.renderer import PygameRenderer
from clauralux.replay.recorder import GameRecorder
from clauralux.runner.headless import GameResult


class VisualRunner:
    """Runs a game with pygame rendering so you can watch it."""

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bots: Mapping[PlayerId, Bot],
        bot_names: Mapping[PlayerId, str] | None = None,
        recorder: GameRecorder | None = None,
        commentary_enabled: bool = True,
        pause_on_events: bool = False,
    ) -> None:
        self._config = config
        self._game = Game(config, initial_state)
        self._bots = bots
        self._bot_names: dict[PlayerId, str] = dict(bot_names) if bot_names else {}
        self._recorder = recorder
        self._renderer = PygameRenderer(config)
        self._paused = False
        self._speed_multiplier = 1

        # Detect human player for mouse input routing.
        self._human_bot: HumanBot | None = None
        self._human_pid: PlayerId | None = None
        for pid, bot in self._bots.items():
            if isinstance(bot, HumanBot):
                self._human_bot = bot
                self._human_pid = pid
                break

        self._commentary = CommentarySystem(
            config=config,
            initial_state=initial_state,
            bot_names=self._bot_names,
            screen_width=self._renderer._window_width,
            screen_height=self._renderer._window_height,
            map_to_screen=self._renderer.map_to_screen,
            enabled=commentary_enabled,
            pause_on_events=pause_on_events,
        )

    @property
    def game(self) -> Game:
        return self._game

    def run(self) -> GameResult:
        """Run the game with visual display. Returns result when done."""
        game = self._game
        cfg = self._config
        renderer = self._renderer

        # Notify bots of game start.
        for player_id, bot in self._bots.items():
            bot.on_game_start(game.get_view(player_id))

        running = True
        while running:
            # Handle pygame events.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and self._human_bot is not None:
                    self._handle_mouse(event)

            if not running:
                break

            # Advance simulation if not paused and game not over.
            if not self._paused and not game.is_over:
                for _ in range(self._speed_multiplier):
                    if game.is_over:
                        break
                    if game.state.tick % cfg.decision_interval == 0:
                        for player_id, bot in self._bots.items():
                            if player_id not in game.state.eliminated:
                                view = game.get_view(player_id)
                                actions = bot.decide(view)
                                if self._recorder is not None:
                                    self._recorder.record_actions(
                                        game.state.tick, player_id, actions
                                    )
                                game.apply_actions(player_id, actions)
                    game.tick()

                    # Update commentary after each tick.
                    intents = {
                        pid: bot.intent
                        for pid, bot in self._bots.items()
                        if pid not in game.state.eliminated
                    }
                    if self._commentary.update(game.state, intents):
                        self._paused = True
                        break

            # Draw with bot intents, speed, and pause state.
            intents = {
                pid: "💀" if pid in game.state.eliminated else bot.intent
                for pid, bot in self._bots.items()
            }
            selected = self._human_bot.selected_sun if self._human_bot else None
            renderer.draw(
                game.state,
                intents,
                speed=self._speed_multiplier,
                paused=self._paused,
                bot_names=self._bot_names,
                overlay_callback=self._commentary.draw,
                selected_sun_id=selected,
            )
            renderer.tick()

        # Notify bots of game end.
        for player_id, bot in self._bots.items():
            bot.on_game_end(game.get_view(player_id))

        renderer.close()

        winner = game.state.winner
        return GameResult(
            winner=winner,
            ticks=game.state.tick,
            eliminated=frozenset(game.state.eliminated),
            is_draw=winner == NEUTRAL,
        )

    def _handle_key(self, key: int) -> bool:
        """Handle a key press. Returns False if we should quit."""
        if key == pygame.K_ESCAPE or key == pygame.K_q:
            return False
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self._paused = not self._paused
            if not self._paused:
                self._commentary.consume_pause()
        elif key == pygame.K_UP:
            max_speed = 4 if self._human_bot else 64
            self._speed_multiplier = min(self._speed_multiplier * 2, max_speed)
        elif key == pygame.K_DOWN:
            self._speed_multiplier = max(self._speed_multiplier // 2, 1)
        return True

    def _handle_mouse(self, event: pygame.event.Event) -> None:
        """Handle a mouse click for the human player."""
        if self._human_bot is None or self._human_pid is None:
            return
        if self._game.is_over:
            return

        # Right-click deselects.
        if event.button == 3:
            self._human_bot.handle_right_click()
            return

        if event.button != 1:
            return

        # Convert screen coords to map coords and find clicked sun.
        mx, my = event.pos
        map_x, map_y = self._renderer.screen_to_map(mx, my)
        clicked_sun_id = self._find_sun_at(map_x, map_y)

        # Get owner of clicked sun (0=neutral if no sun).
        clicked_owner = 0
        if clicked_sun_id is not None:
            sun = self._game.state.suns.get(clicked_sun_id)
            if sun is not None:
                clicked_owner = int(sun.owner)

        shift_held = pygame.key.get_mods() & pygame.KMOD_SHIFT != 0
        view = self._game.get_view(self._human_pid)
        self._human_bot.handle_click(
            clicked_sun_id,
            clicked_owner,
            int(self._human_pid),
            view,
            shift_held,
        )

    def _find_sun_at(self, map_x: float, map_y: float) -> SunId | None:
        """Find the sun at the given map coordinates, or None."""
        best_id: SunId | None = None
        best_dist = float("inf")
        for sid, sun in self._game.state.suns.items():
            dx = sun.position.x - map_x
            dy = sun.position.y - map_y
            dist = (dx * dx + dy * dy) ** 0.5
            hit_radius = 18 + (sun.level - 1) * 6 + 10  # generous click target
            if dist < hit_radius and dist < best_dist:
                best_dist = dist
                best_id = sid
        return best_id
