from __future__ import annotations

from collections.abc import Mapping

import pygame

from clauralux.bots.base import Bot
from clauralux.engine.config import GameConfig
from clauralux.engine.game import Game
from clauralux.engine.state import GameState
from clauralux.engine.types import PlayerId
from clauralux.renderer.renderer import PygameRenderer
from clauralux.runner.headless import GameResult

from .headless import NEUTRAL


class VisualRunner:
    """Runs a game with pygame rendering so you can watch it."""

    def __init__(
        self,
        config: GameConfig,
        initial_state: GameState,
        bots: Mapping[PlayerId, Bot],
    ) -> None:
        self._config = config
        self._game = Game(config, initial_state)
        self._bots = bots
        self._renderer = PygameRenderer(config)
        self._paused = False
        self._speed_multiplier = 1

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
                                game.apply_actions(player_id, actions)
                    game.tick()

            # Draw with bot intents.
            intents = {pid: bot.intent for pid, bot in self._bots.items()}
            renderer.draw(game.state, intents)
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
        elif key == pygame.K_SPACE:
            self._paused = not self._paused
        elif key == pygame.K_UP:
            self._speed_multiplier = min(self._speed_multiplier * 2, 64)
        elif key == pygame.K_DOWN:
            self._speed_multiplier = max(self._speed_multiplier // 2, 1)
        return True
