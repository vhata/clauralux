"""Human-controlled bot — receives actions from mouse clicks via the visual runner.

The visual runner detects that P1 is a HumanBot and routes mouse events to it.
Click your own sun to select it, click another sun to send units there, and
click a selected sun again to upgrade it.
"""

from __future__ import annotations

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.types import SunId
from clauralux.engine.view import GameView

from .base import Bot


class HumanBot(Bot):
    """A bot controlled by mouse clicks. Actions are queued externally."""

    def __init__(self) -> None:
        super().__init__()
        self._action_queue: list[Action] = []
        self.selected_sun: SunId | None = None

    def decide(self, view: GameView) -> list[Action]:
        # Deselect if the selected sun is no longer ours.
        if self.selected_sun is not None:
            sun = view.sun_by_id(self.selected_sun)
            if sun is None or sun.owner != view.my_id:
                self.selected_sun = None

        actions = list(self._action_queue)
        self._action_queue.clear()

        if self.selected_sun is not None:
            sun = view.sun_by_id(self.selected_sun)
            if sun is not None:
                self._intent = f"Selected Sun {self.selected_sun} ({sun.garrison} units)"
            else:
                self._intent = "Waiting for orders."
        else:
            self._intent = "Click a sun to select it."

        return actions

    def handle_click(
        self,
        clicked_sun_id: SunId | None,
        clicked_sun_owner: int,
        my_id: int,
        view: GameView,
        shift_held: bool = False,
    ) -> None:
        """Process a mouse click on the game map.

        Called by the visual runner with the sun that was clicked (or None
        if empty space was clicked).
        """
        if clicked_sun_id is None:
            # Clicked empty space — deselect.
            self.selected_sun = None
            return

        if self.selected_sun is None:
            # No selection — select own sun.
            if clicked_sun_owner == my_id:
                self.selected_sun = clicked_sun_id
            return

        if clicked_sun_id == self.selected_sun:
            # Clicked the already-selected sun — upgrade it.
            self._action_queue.append(UpgradeSun(clicked_sun_id))
            self._intent = f"Upgrading Sun {clicked_sun_id}!"
            return

        if clicked_sun_owner == my_id:
            # Clicked a different own sun — switch selection.
            self.selected_sun = clicked_sun_id
            return

        # Clicked enemy or neutral sun — send units from selected sun.
        sun = view.sun_by_id(self.selected_sun)
        if sun is None:
            self.selected_sun = None
            return

        reserve = 3
        if shift_held:
            count = max(1, int((sun.garrison - reserve) / 2))
        else:
            count = max(1, int(sun.garrison - reserve))

        if count > 0:
            self._action_queue.append(SendUnits(self.selected_sun, clicked_sun_id, count))
            self._intent = f"Sending {count} units to Sun {clicked_sun_id}!"

    def handle_right_click(self) -> None:
        """Right-click deselects."""
        self.selected_sun = None
