from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

PlayerId = NewType("PlayerId", int)
SunId = NewType("SunId", int)
Tick = NewType("Tick", int)

NEUTRAL: PlayerId = PlayerId(0)


@dataclass(frozen=True, slots=True)
class Position:
    """A 2D point on the game map."""

    x: float
    y: float

    def distance_to(self, other: Position) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return float((dx * dx + dy * dy) ** 0.5)

    def direction_to(self, other: Position) -> tuple[float, float]:
        """Return a unit vector pointing from self toward other."""
        dist = self.distance_to(other)
        if dist == 0:
            return (0.0, 0.0)
        return ((other.x - self.x) / dist, (other.y - self.y) / dist)
