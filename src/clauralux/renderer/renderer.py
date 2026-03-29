from __future__ import annotations

import math

import pygame

from clauralux.engine.config import GameConfig
from clauralux.engine.state import GameState
from clauralux.engine.types import NEUTRAL, PlayerId, SunId

from .colors import BACKGROUND, TEXT, TEXT_DIM, get_bright_color, get_color

# Padding around the game map within the window.
PADDING = 40
HUD_HEIGHT = 100


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

    def draw(
        self,
        state: GameState,
        intents: dict[PlayerId, str] | None = None,
        speed: int = 1,
        paused: bool = False,
        bot_names: dict[PlayerId, str] | None = None,
    ) -> None:
        """Draw the full game state."""
        self._update_flash_events(state)
        self._screen.fill(BACKGROUND)
        self._draw_trajectories(state)
        self._draw_unit_groups(state)
        self._draw_flash_events()
        self._draw_suns(state)
        self._draw_hud(state, intents or {}, speed=speed, paused=paused, bot_names=bot_names or {})
        if paused and not state.winner:
            self._draw_pause_overlay(state, intents or {}, bot_names or {})
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

    def _draw_hud(
        self,
        state: GameState,
        intents: dict[PlayerId, str] | None = None,
        speed: int = 1,
        paused: bool = False,
        bot_names: dict[PlayerId, str] | None = None,
    ) -> None:
        hud_y = self._window_height - HUD_HEIGHT + 10

        # Tick counter + speed.
        speed_label = "PAUSED" if paused else f"{speed}x"
        tick_text = f"Tick: {state.tick}  [{speed_label}]"
        tick_surface = self._font.render(tick_text, True, TEXT_DIM)
        self._screen.blit(tick_surface, (PADDING, hud_y))

        # Compute column layout based on player count.
        num_players = len(state.players)
        left_margin = 120
        available_width = self._window_width - left_margin - PADDING
        col_width = max(120, available_width // max(num_players, 1))

        # Player stats.
        for i, player_id in enumerate(state.players):
            x = left_margin + i * col_width
            color = get_color(player_id)
            suns_owned = sum(1 for s in state.suns.values() if s.owner == player_id)
            total_garrison = sum(
                int(s.garrison) for s in state.suns.values() if s.owner == player_id
            )
            units_in_flight = sum(g.count for g in state.unit_groups if g.owner == player_id)
            eliminated = player_id in state.eliminated

            bot_name = (bot_names or {}).get(player_id, "")
            name_tag = f" ({bot_name})" if bot_name else ""
            if eliminated:
                label = f"P{player_id}{name_tag}: OUT"
            else:
                label = f"P{player_id}{name_tag}: {suns_owned}s {total_garrison}+{units_in_flight}u"

            label_surface = self._font.render(label, True, color)
            self._screen.blit(label_surface, (x, hud_y))

        # Garrison proportion bars.
        bar_y = hud_y + 20
        total_all = max(
            1,
            sum(int(s.garrison) for s in state.suns.values() if s.owner != NEUTRAL)
            + sum(g.count for g in state.unit_groups),
        )
        bar_max_width = col_width - 10
        for i, player_id in enumerate(state.players):
            x = left_margin + i * col_width
            color = get_color(player_id)
            player_total = sum(
                int(s.garrison) for s in state.suns.values() if s.owner == player_id
            ) + sum(g.count for g in state.unit_groups if g.owner == player_id)
            fill = int(bar_max_width * player_total / total_all)
            pygame.draw.rect(self._screen, (40, 40, 50), (x, bar_y, bar_max_width, 5))
            pygame.draw.rect(self._screen, color, (x, bar_y, fill, 5))

        # Bot intents.
        if intents:
            intent_y = bar_y + 12
            max_chars = max(10, col_width // 8)
            for i, player_id in enumerate(state.players):
                x = left_margin + i * col_width
                color = get_color(player_id)
                intent_text = intents.get(player_id, "")
                if intent_text:
                    if len(intent_text) > max_chars:
                        intent_text = intent_text[: max_chars - 1] + "…"
                    intent_surface = self._font.render(intent_text, True, color)
                    self._screen.blit(intent_surface, (x, intent_y))

        # Winner banner.
        if state.winner is not None:
            banner = "DRAW!" if state.winner == NEUTRAL else f"PLAYER {state.winner} WINS!"
            banner_surface = self._font_large.render(banner, True, TEXT)
            banner_rect = banner_surface.get_rect(center=(self._window_width // 2, hud_y + 35))
            self._screen.blit(banner_surface, banner_rect)

    def _draw_pause_overlay(
        self,
        state: GameState,
        intents: dict[PlayerId, str],
        bot_names: dict[PlayerId, str],
    ) -> None:
        """Draw a detailed status overlay when paused."""
        # Semi-transparent backdrop.
        overlay = pygame.Surface((self._window_width, self._window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._screen.blit(overlay, (0, 0))

        # Title.
        title = self._font_large.render("PAUSED — Player Status", True, TEXT)
        title_rect = title.get_rect(center=(self._window_width // 2, 30))
        self._screen.blit(title, title_rect)

        # Compute per-player stats.
        cfg = self._config
        panel_width = min(350, (self._window_width - 60) // max(len(state.players), 1))
        total_width = panel_width * len(state.players)
        start_x = (self._window_width - total_width) // 2

        for i, pid in enumerate(state.players):
            x = start_x + i * panel_width
            color = get_color(pid)
            bright = get_bright_color(pid)
            eliminated = pid in state.eliminated

            my_suns = [s for s in state.suns.values() if s.owner == pid]
            suns_owned = len(my_suns)
            total_garrison = sum(int(s.garrison) for s in my_suns)
            total_levels = sum(s.level for s in my_suns)
            max_level = max((s.level for s in my_suns), default=0)
            production_rate = total_levels * cfg.production_per_level
            units_in_flight = sum(g.count for g in state.unit_groups if g.owner == pid)
            total_units = total_garrison + units_in_flight

            # Incoming threats: enemy units heading toward this player's suns.
            my_sun_ids = {s.id for s in my_suns}
            incoming_threats = sum(
                g.count
                for g in state.unit_groups
                if g.owner != pid and g.target_sun_id in my_sun_ids
            )

            bot_name = bot_names.get(pid, "???")
            intent = intents.get(pid, "")

            # Draw panel.
            y = 60
            line_h = 20

            # Header.
            header = f"P{pid}: {bot_name}"
            header_surface = self._font_large.render(header, True, bright)
            self._screen.blit(header_surface, (x + 10, y))
            y += line_h + 8

            if eliminated:
                elim_surface = self._font.render("ELIMINATED", True, (180, 60, 60))
                self._screen.blit(elim_surface, (x + 10, y))
                y += line_h * 2
                continue

            # Stats lines.
            lines = [
                f"Suns: {suns_owned} (max lvl {max_level})",
                f"Garrison: {total_garrison}",
                f"In flight: {units_in_flight}",
                f"Total units: {total_units}",
                f"Production: {production_rate} per {cfg.production_interval} ticks",
                f"Incoming threats: {incoming_threats}",
            ]

            for line in lines:
                line_surface = self._font.render(line, True, color)
                self._screen.blit(line_surface, (x + 10, y))
                y += line_h

            # Sun breakdown.
            y += 5
            breakdown_header = self._font.render("Suns:", True, TEXT_DIM)
            self._screen.blit(breakdown_header, (x + 10, y))
            y += line_h
            for sun in sorted(my_suns, key=lambda s: -s.garrison):
                sun_line = f"  #{sun.id}: lvl {sun.level}, garrison {int(sun.garrison)}"
                sun_surface = self._font.render(sun_line, True, color)
                self._screen.blit(sun_surface, (x + 10, y))
                y += line_h

            # Intent.
            y += 5
            thinking_header = self._font.render("Thinking:", True, TEXT_DIM)
            self._screen.blit(thinking_header, (x + 10, y))
            y += line_h
            if intent:
                # Word-wrap intent text.
                max_chars = max(15, (panel_width - 20) // 8)
                while intent:
                    chunk = intent[:max_chars]
                    intent = intent[max_chars:]
                    intent_surface = self._font.render(f"  {chunk}", True, color)
                    self._screen.blit(intent_surface, (x + 10, y))
                    y += line_h

        # Footer hint.
        hint = self._font.render("Press SPACE to resume", True, TEXT_DIM)
        hint_rect = hint.get_rect(center=(self._window_width // 2, self._window_height - 20))
        self._screen.blit(hint, hint_rect)

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
