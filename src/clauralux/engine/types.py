from __future__ import annotations

from typing import NewType

from clauralux._engine import Position

PlayerId = NewType("PlayerId", int)
SunId = NewType("SunId", int)
Tick = NewType("Tick", int)

NEUTRAL: PlayerId = PlayerId(0)

__all__ = ["NEUTRAL", "PlayerId", "Position", "SunId", "Tick"]
