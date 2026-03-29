from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pygame

from clauralux.engine.types import PlayerId

from .colors import BACKGROUND, TEXT, TEXT_DIM, get_color

# Colour names for labelling player slots.
PLAYER_COLOUR_NAMES: dict[int, str] = {
    1: "Blue",
    2: "Red",
    3: "Green",
    4: "Yellow",
    5: "Purple",
    6: "Orange",
}


@dataclass
class MenuOption:
    """A single configurable option in the menu."""

    key: str  # internal identifier
    label: str  # display name
    description: str | Callable[[str], str]  # static text, or callback(current_value) -> text
    choices: list[str]  # available values to cycle through
    default_index: int = 0  # index into choices
    current_index: int = field(init=False)
    # Optional callback: receives all current option values, returns True if visible.
    visible_when: Callable[[dict[str, str]], bool] | None = None

    def __post_init__(self) -> None:
        self.current_index = self.default_index

    @property
    def value(self) -> str:
        return self.choices[self.current_index]

    @property
    def current_description(self) -> str:
        if callable(self.description):
            return self.description(self.value)
        return self.description

    def next(self) -> None:
        self.current_index = (self.current_index + 1) % len(self.choices)

    def prev(self) -> None:
        self.current_index = (self.current_index - 1) % len(self.choices)


class MenuScreen:
    """A data-driven pygame menu. Options are built from registries."""

    def __init__(self, options: list[MenuOption], title: str = "CLAURALUX") -> None:
        self._options = options
        self._title = title
        self._selected = 0  # index into _visible_options
        self._width = 800
        self._height = 600

        pygame.init()
        self._screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(title)
        self._font = pygame.font.SysFont("monospace", 16)
        self._font_large = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_small = pygame.font.SysFont("monospace", 13)

    def _current_values(self) -> dict[str, str]:
        return {opt.key: opt.value for opt in self._options}

    def _visible_options(self) -> list[MenuOption]:
        values = self._current_values()
        return [
            opt for opt in self._options if opt.visible_when is None or opt.visible_when(values)
        ]

    def run(self) -> dict[str, str] | None:
        """Show menu, return dict of key->value when Enter pressed, or None on quit."""
        clock = pygame.time.Clock()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None
                if event.type == pygame.KEYDOWN:
                    result = self._handle_key(event.key)
                    if result is not None:
                        pygame.quit()
                        return result

            self._draw()
            clock.tick(30)

    def _handle_key(self, key: int) -> dict[str, str] | None:
        visible = self._visible_options()
        if not visible:
            return None

        # Clamp selection to visible range.
        self._selected = min(self._selected, len(visible) - 1)

        if key in (pygame.K_ESCAPE, pygame.K_q):
            return None
        elif key == pygame.K_UP:
            self._selected = (self._selected - 1) % len(visible)
        elif key == pygame.K_DOWN:
            self._selected = (self._selected + 1) % len(visible)
        elif key in (pygame.K_RIGHT, pygame.K_TAB):
            visible[self._selected].next()
        elif key == pygame.K_LEFT:
            visible[self._selected].prev()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._current_values()
        return None

    def _draw(self) -> None:
        self._screen.fill(BACKGROUND)
        visible = self._visible_options()
        self._selected = min(self._selected, max(0, len(visible) - 1))

        # Title.
        title_surface = self._font_large.render(self._title, True, TEXT)
        title_rect = title_surface.get_rect(center=(self._width // 2, 40))
        self._screen.blit(title_surface, title_rect)

        # Subtitle.
        sub = "UP/DOWN navigate, LEFT/RIGHT change, ENTER start"
        sub_surface = self._font_small.render(sub, True, TEXT_DIM)
        sub_rect = sub_surface.get_rect(center=(self._width // 2, 72))
        self._screen.blit(sub_surface, sub_rect)

        # Layout: options scroll in the area between header and footer.
        options_top = 110
        row_height = 32
        footer_height = 80  # description + prompt
        options_bottom = self._height - footer_height
        max_visible_rows = max(1, (options_bottom - options_top) // row_height)

        # Compute scroll offset to keep selected item visible.
        scroll = 0
        if len(visible) > max_visible_rows:
            # Keep selection roughly centred, clamped to edges.
            scroll = self._selected - max_visible_rows // 2
            scroll = max(0, min(scroll, len(visible) - max_visible_rows))

        # Options.
        y = options_top
        for i in range(scroll, min(scroll + max_visible_rows, len(visible))):
            opt = visible[i]
            is_selected = i == self._selected

            # Use player colour for bot options.
            player_num = None
            if opt.key.startswith("bot") and opt.key[3:].isdigit():
                player_num = int(opt.key[3:])

            label_color = TEXT if is_selected else TEXT_DIM
            if player_num and is_selected:
                value_color = get_color(PlayerId(player_num))
            elif is_selected:
                value_color = get_color(PlayerId(1))
            else:
                value_color = TEXT

            # Label.
            label_surface = self._font.render(f"  {opt.label}:", True, label_color)
            self._screen.blit(label_surface, (60, y))

            # Value with arrows.
            value_text = f"< {opt.value} >" if is_selected else f"  {opt.value}  "
            value_surface = self._font.render(value_text, True, value_color)
            self._screen.blit(value_surface, (350, y))

            # Selection indicator.
            if is_selected:
                indicator_color = (
                    get_color(PlayerId(player_num)) if player_num else get_color(PlayerId(1))
                )
                pygame.draw.circle(self._screen, indicator_color, (40, y + 8), 5)

            y += row_height

        # Scroll indicators.
        if scroll > 0:
            arrow_up = self._font_small.render("▲ more above", True, TEXT_DIM)
            self._screen.blit(arrow_up, (60, options_top - 18))
        if scroll + max_visible_rows < len(visible):
            arrow_down = self._font_small.render("▼ more below", True, TEXT_DIM)
            self._screen.blit(arrow_down, (60, options_bottom - 16))

        # Description of selected option (pinned to bottom).
        desc_y = self._height - footer_height + 10
        pygame.draw.line(self._screen, TEXT_DIM, (60, desc_y - 10), (self._width - 60, desc_y - 10))
        if visible:
            desc = visible[self._selected].current_description
            desc_surface = self._font_small.render(desc, True, TEXT_DIM)
            self._screen.blit(desc_surface, (60, desc_y))

        # Start prompt.
        prompt_y = self._height - 30
        prompt_surface = self._font.render("Press ENTER to start  |  Q to quit", True, TEXT)
        prompt_rect = prompt_surface.get_rect(center=(self._width // 2, prompt_y))
        self._screen.blit(prompt_surface, prompt_rect)

        pygame.display.flip()
