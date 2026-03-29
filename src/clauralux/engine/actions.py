from __future__ import annotations

from dataclasses import dataclass

from .types import SunId


@dataclass(frozen=True, slots=True)
class SendUnits:
    """Send units from one sun to another."""

    source_sun_id: SunId
    target_sun_id: SunId
    count: int  # clamped to available garrison by the engine


@dataclass(frozen=True, slots=True)
class UpgradeSun:
    """Spend garrison units to upgrade a sun's level."""

    sun_id: SunId


Action = SendUnits | UpgradeSun
