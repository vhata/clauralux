from __future__ import annotations

from clauralux._engine import SendUnits, UpgradeSun

Action = SendUnits | UpgradeSun

__all__ = ["Action", "SendUnits", "UpgradeSun"]
