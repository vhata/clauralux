from __future__ import annotations

import math

import pygame

from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId, SunId

from .colors import BACKGROUND, TEXT, TEXT_DIM, get_bright_color, get_color

# Padding around the game map within the window.
PADDING = 40
HUD_HEIGHT = 60


class PygameRenderer:
    """Renders the game state using pygame."""

    def __init__(self, config: GameConfig, title: str = "Clauralux") -> None:
        self._config = config
        self._window_width = int(config.map_width) + PADDING * 2
        self._window_height = int(config.map_height) + PADDING * 2 + HUD_HEIGHT
        self._offset_x = PADDING
        self._offset_y = PADDING

        pygame.init()
        self._screen = pygame.display.set_mode((self._window_width, self._window_height))
        pygame.display.set_caption(title)
        self._font = pygame.font.SysFont("monospace", 14)
        self._font_large = pygame.font.SysFont("monospace", 18, bold=True)
        self._clock = pygame.time.Clock()

        # State for capture flash animations.
        self._prev_owners: dict[SunId, PlayerId] = {}
        self._flash_events: list[tuple[int, int, int, tuple[int, int, int]]] = []

    def close(self) -> None:
        pygame.quit()

    def tick(self) -> None:
        """Limit frame rate to config.ticks_per_second."""
        self._clock.tick(self._config.ticks_per_second)

    def draw(self, state: GameState) -> None:
        """Draw the full game state."""
        self._update_flash_events(state)
        self._screen.fill(BACKGROUND)
        self._draw_trajectories(state)
        self._draw_unit_groups(state)
        self._draw_flash_events()
        self._draw_suns(state)
        self._draw_hud(state)
        pygame.display.flip()

    def map_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert game map coordinates to screen pixel coordinates."""
        return (int(x) + self._offset_x, int(y) + self._offset_y)

    def screen_to_map(self, sx: int, sy: int) -> tuple[float, float]:
        """Convert screen pixel coordinates to game map coordinates."""
        return (float(sx - self._offset_x), float(sy - self._offset_y))

    def _draw_trajectories(self, state: GameState) -> None:
        """Draw faint dashed lines from unit groups to their target suns."""
        for group in state.unit_groups:
            target = state.suns.get(group.target_sun_id)
            if target is None:
                continue
            sx, sy = self.map_to_screen(group.position.x, group.position.y)
            tx, ty = self.map_to_screen(target.position.x, target.position.y)
            color = (*get_color(group.owner), 35)

            # Draw dashed line: 6px on, 6px off.
            dx = tx - sx
            dy = ty - sy
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1:
                continue
            ux, uy = dx / length, dy / length

            dash_surface = pygame.Surface(
                (self._window_width, self._window_height), pygame.SRCALPHA
            )
            pos = 0.0
            while pos < length:
                end = min(pos + 6, length)
                x1 = int(sx + ux * pos)
                y1 = int(sy + uy * pos)
                x2 = int(sx + ux * end)
                y2 = int(sy + uy * end)
                pygame.draw.line(dash_surface, color, (x1, y1), (x2, y2), 1)
                pos += 12  # 6 on + 6 off
            self._screen.blit(dash_surface, (0, 0))

    def _draw_suns(self, state: GameState) -> None:
        for sun in state.suns.values():
            sx, sy = self.map_to_screen(sun.position.x, sun.position.y)
            color = get_color(sun.owner)

            # Sun size scales with level.
            base_radius = 18
            radius = base_radius + (sun.level - 1) * 6

            # Outer glow — pulses for owned suns, static for neutral.
            if sun.owner != NEUTRAL:
                pulse = 0.5 + 0.5 * math.sin(state.tick * 0.05 + sun.id * 1.7)
                glow_radius = radius + 6 + int(pulse * 4)
                glow_alpha = 30 + int(pulse * 25)
            else:
                glow_radius = radius + 8
                glow_alpha = 40
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_color = (*color, glow_alpha)
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
            self._screen.blit(glow_surface, (sx - glow_radius, sy - glow_radius))

            # Main circle.
            pygame.draw.circle(self._screen, color, (sx, sy), radius)

            # Level indicator: concentric rings.
            if sun.level >= 2:
                pygame.draw.circle(self._screen, BACKGROUND, (sx, sy), radius - 4, 2)
            if sun.level >= 3:
                pygame.draw.circle(self._screen, BACKGROUND, (sx, sy), radius - 9, 2)

            # Garrison count.
            garrison_text = str(int(sun.garrison))
            text_surface = self._font.render(garrison_text, True, TEXT)
            text_rect = text_surface.get_rect(center=(sx, sy))
            self._screen.blit(text_surface, text_rect)

    def _draw_unit_groups(self, state: GameState) -> None:
        for group in state.unit_groups:
            sx, sy = self.map_to_screen(group.position.x, group.position.y)
            color = get_bright_color(group.owner)

            # Render as a small swarm of dots rather than one big circle.
            num_dots = min(group.count, 8)
            spread = min(4 + group.count, 12)

            for i in range(num_dots):
                # Deterministic scatter using a simple hash-like offset.
                angle = i * 2.399 + group.count * 0.7  # golden angle spiral
                r = spread * (0.3 + 0.7 * ((i + 1) / num_dots))
                dot_x = int(sx + math.cos(angle) * r)
                dot_y = int(sy + math.sin(angle) * r)
                pygame.draw.circle(self._screen, color, (dot_x, dot_y), 2)

            # Small count label for larger groups.
            if group.count >= 5:
                count_text = self._font.render(str(group.count), True, TEXT_DIM)
                self._screen.blit(count_text, (sx + spread + 2, sy - 6))

    def _draw_hud(self, state: GameState) -> None:
        hud_y = self._window_height - HUD_HEIGHT + 10

        # Tick counter.
        tick_text = f"Tick: {state.tick}"
        tick_surface = self._font.render(tick_text, True, TEXT_DIM)
        self._screen.blit(tick_surface, (PADDING, hud_y))

        # Player stats.
        x_offset = 200
        for player_id in state.players:
            color = get_color(player_id)
            suns_owned = sum(1 for s in state.suns.values() if s.owner == player_id)
            total_garrison = sum(
                int(s.garrison) for s in state.suns.values() if s.owner == player_id
            )
            units_in_flight = sum(g.count for g in state.unit_groups if g.owner == player_id)
            eliminated = player_id in state.eliminated

            if eliminated:
                label = f"P{player_id}: ELIMINATED"
            else:
                label = f"P{player_id}: {suns_owned}suns {total_garrison}+{units_in_flight}units"

            label_surface = self._font.render(label, True, color)
            self._screen.blit(label_surface, (x_offset, hud_y))
            x_offset += 300

        # Garrison proportion bars.
        bar_y = hud_y + 22
        total_all = max(
            1,
            sum(int(s.garrison) for s in state.suns.values() if s.owner != NEUTRAL)
            + sum(g.count for g in state.unit_groups),
        )
        bar_x = 200
        bar_width = 250
        for player_id in state.players:
            color = get_color(player_id)
            player_total = sum(
                int(s.garrison) for s in state.suns.values() if s.owner == player_id
            ) + sum(g.count for g in state.unit_groups if g.owner == player_id)
            fill = int(bar_width * player_total / total_all)
            pygame.draw.rect(self._screen, (40, 40, 50), (bar_x, bar_y, bar_width, 6))
            pygame.draw.rect(self._screen, color, (bar_x, bar_y, fill, 6))
            bar_x += 300

        # Winner banner.
        if state.winner is not None:
            banner = "DRAW!" if state.winner == NEUTRAL else f"PLAYER {state.winner} WINS!"
            banner_surface = self._font_large.render(banner, True, TEXT)
            banner_rect = banner_surface.get_rect(center=(self._window_width // 2, hud_y + 35))
            self._screen.blit(banner_surface, banner_rect)

    def _update_flash_events(self, state: GameState) -> None:
        """Detect ownership changes and spawn flash animations."""
        for sun_id, sun in state.suns.items():
            prev = self._prev_owners.get(sun_id)
            if prev is not None and prev != sun.owner:
                sx, sy = self.map_to_screen(sun.position.x, sun.position.y)
                color = get_bright_color(sun.owner)
                self._flash_events.append((sx, sy, 20, color))  # 20 frames
            self._prev_owners[sun_id] = sun.owner

    def _draw_flash_events(self) -> None:
        """Draw and decay capture flash animations."""
        remaining: list[tuple[int, int, int, tuple[int, int, int]]] = []
        for sx, sy, frames_left, color in self._flash_events:
            alpha = int(255 * frames_left / 20)
            radius = 30 + (20 - frames_left) * 3
            flash_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            flash_color = (*color, alpha)
            pygame.draw.circle(flash_surface, flash_color, (radius, radius), radius, 3)
            self._screen.blit(flash_surface, (sx - radius, sy - radius))
            if frames_left > 1:
                remaining.append((sx, sy, frames_left - 1, color))
        self._flash_events = remaining
