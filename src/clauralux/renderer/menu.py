from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from clauralux.engine.types import PlayerId

from .colors import BACKGROUND, TEXT, TEXT_DIM, get_color


@dataclass
class MenuOption:
    """A single configurable option in the menu."""

    key: str  # internal identifier
    label: str  # display name
    description: str  # help text shown when selected
    choices: list[str]  # available values to cycle through
    default_index: int = 0  # index into choices
    current_index: int = field(init=False)

    def __post_init__(self) -> None:
        self.current_index = self.default_index

    @property
    def value(self) -> str:
        return self.choices[self.current_index]

    def next(self) -> None:
        self.current_index = (self.current_index + 1) % len(self.choices)

    def prev(self) -> None:
        self.current_index = (self.current_index - 1) % len(self.choices)


class MenuScreen:
    """A data-driven pygame menu. Options are built from registries."""

    def __init__(self, options: list[MenuOption], title: str = "CLAURALUX") -> None:
        self._options = options
        self._title = title
        self._selected = 0  # currently highlighted option
        self._width = 800
        self._height = 500 + len(options) * 40

        pygame.init()
        self._screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(title)
        self._font = pygame.font.SysFont("monospace", 16)
        self._font_large = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_small = pygame.font.SysFont("monospace", 13)

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
        if key == pygame.K_ESCAPE or key == pygame.K_q:
            return None  # signal quit via the run() method
        elif key == pygame.K_UP:
            self._selected = (self._selected - 1) % len(self._options)
        elif key == pygame.K_DOWN:
            self._selected = (self._selected + 1) % len(self._options)
        elif key in (pygame.K_RIGHT, pygame.K_TAB):
            self._options[self._selected].next()
        elif key == pygame.K_LEFT:
            self._options[self._selected].prev()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return {opt.key: opt.value for opt in self._options}
        return None

    def _draw(self) -> None:
        self._screen.fill(BACKGROUND)

        # Title.
        title_surface = self._font_large.render(self._title, True, TEXT)
        title_rect = title_surface.get_rect(center=(self._width // 2, 40))
        self._screen.blit(title_surface, title_rect)

        # Subtitle.
        sub = "Use UP/DOWN to navigate, LEFT/RIGHT to change, ENTER to start"
        sub_surface = self._font_small.render(sub, True, TEXT_DIM)
        sub_rect = sub_surface.get_rect(center=(self._width // 2, 72))
        self._screen.blit(sub_surface, sub_rect)

        # Options.
        y = 110
        for i, opt in enumerate(self._options):
            is_selected = i == self._selected
            label_color = TEXT if is_selected else TEXT_DIM
            value_color = get_color(PlayerId(1)) if is_selected else TEXT

            # Label.
            label_surface = self._font.render(f"  {opt.label}:", True, label_color)
            self._screen.blit(label_surface, (60, y))

            # Value with arrows.
            value_text = f"< {opt.value} >" if is_selected else f"  {opt.value}  "
            value_surface = self._font.render(value_text, True, value_color)
            self._screen.blit(value_surface, (350, y))

            # Selection indicator.
            if is_selected:
                pygame.draw.circle(self._screen, get_color(PlayerId(1)), (40, y + 8), 5)

            y += 32

        # Description of selected option.
        desc_y = y + 20
        pygame.draw.line(self._screen, TEXT_DIM, (60, desc_y - 10), (self._width - 60, desc_y - 10))
        desc = self._options[self._selected].description
        desc_surface = self._font_small.render(desc, True, TEXT_DIM)
        self._screen.blit(desc_surface, (60, desc_y))

        # Start prompt.
        prompt_y = desc_y + 40
        prompt_surface = self._font.render("Press ENTER to start  |  Q to quit", True, TEXT)
        prompt_rect = prompt_surface.get_rect(center=(self._width // 2, prompt_y))
        self._screen.blit(prompt_surface, prompt_rect)

        pygame.display.flip()
