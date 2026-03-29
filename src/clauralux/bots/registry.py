"""Central bot registry — single source of truth for all bot types.

Add new bots here. They'll automatically appear in the CLI, GUI menu,
and training opponent pool.
"""

from __future__ import annotations

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.base import Bot
from clauralux.bots.evolved import EvolvedBot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.opportunist import OpportunistBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.bots.rush import RushBot
from clauralux.bots.sniper import SniperBot
from clauralux.bots.turtle import TurtleBot

# Every bot in the game. Add new bots here and they'll be available everywhere.
BOT_REGISTRY: dict[str, type[Bot]] = {
    "passive": PassiveBot,
    "random": RandomBot,
    "aggressive": AggressiveBot,
    "expander": ExpanderBot,
    "turtle": TurtleBot,
    "rush": RushBot,
    "sniper": SniperBot,
    "opportunist": OpportunistBot,
    "evolved": EvolvedBot,
}

BOT_DESCRIPTIONS: dict[str, str] = {
    "passive": "Does nothing. Just sits there.",
    "random": "Picks actions by dice roll. Chaotic and bad.",
    "aggressive": "Waits until it can overwhelm the weakest target, then sends everything.",
    "expander": "Grabs neutrals first, upgrades economy, attacks enemies last.",
    "turtle": "Upgrades all suns to max, builds huge garrisons, then crushes.",
    "rush": "Constant early pressure — sends units every 20 ticks at the nearest target.",
    "sniper": "Ignores neutrals. Targets the weakest player's weakest sun to eliminate them.",
    "opportunist": "Watches for low garrisons and pounces. Upgrades when nothing's weak enough.",
    "evolved": "Evolved strategy — trained by playing thousands of games against all other bots.",
}

# Bots excluded from training: passive is useless as an opponent,
# evolved is the thing being trained.
_TRAINING_EXCLUDED: set[str] = {"passive", "evolved"}


def training_opponents() -> list[type[Bot]]:
    """Return all bot classes that should be used as training opponents."""
    return [cls for name, cls in BOT_REGISTRY.items() if name not in _TRAINING_EXCLUDED]
