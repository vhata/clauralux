"""Central bot registry — single source of truth for all bot types.

Add new bots here. They'll automatically appear in the CLI, GUI menu,
and training opponent pool.
"""

from __future__ import annotations

from clauralux.bots.aggressive import AggressiveBot
from clauralux.bots.baiter import BaiterBot
from clauralux.bots.base import Bot
from clauralux.bots.coordinator import CoordinatorBot
from clauralux.bots.economic import EconomicBot
from clauralux.bots.evolved import EvolvedBot
from clauralux.bots.expander import ExpanderBot
from clauralux.bots.human import HumanBot
from clauralux.bots.neural import NeuralBot
from clauralux.bots.opportunist import OpportunistBot
from clauralux.bots.passive import PassiveBot
from clauralux.bots.random_bot import RandomBot
from clauralux.bots.reactive import ReactiveBot
from clauralux.bots.rush import RushBot
from clauralux.bots.sniper import SniperBot
from clauralux.bots.swarm import SwarmBot
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
    "swarm": SwarmBot,
    "coordinator": CoordinatorBot,
    "reactive": ReactiveBot,
    "economic": EconomicBot,
    "baiter": BaiterBot,
    "evolved": EvolvedBot,
    "neural": NeuralBot,
    "human": HumanBot,
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
    "swarm": "Many small attacks from every sun. Death by a thousand cuts.",
    "coordinator": "Accumulates, then strikes multiple targets simultaneously.",
    "reactive": "Defensive — reinforces threatened suns, only attacks with overwhelming force.",
    "economic": "Upgrades aggressively, then targets the opponent's highest-level suns.",
    "baiter": "Sends small bait attacks to draw defenders, then hits the weakened suns.",
    "evolved": "Evolved strategy — trained by playing thousands of games against all other bots.",
    "neural": "Neural net bot — MLP reads game state and adapts strategy each tick.",
    "human": "You! Click suns to select, click targets to attack, click selected to upgrade.",
}

# Bots excluded from training: passive is useless as an opponent,
# evolved is the thing being trained.
_TRAINING_EXCLUDED: set[str] = {"passive", "evolved", "neural", "human"}


def training_opponents() -> list[type[Bot]]:
    """Return all bot classes that should be used as training opponents."""
    return [cls for name, cls in BOT_REGISTRY.items() if name not in _TRAINING_EXCLUDED]


# Difficulty weights for training fitness — harder opponents count more.
BOT_DIFFICULTY: dict[str, float] = {
    "random": 0.5,
    "aggressive": 0.8,
    "rush": 0.8,
    "swarm": 0.7,
    "expander": 1.0,
    "economic": 1.0,
    "opportunist": 1.0,
    "reactive": 1.1,
    "turtle": 1.2,
    "coordinator": 1.2,
    "sniper": 1.3,
    "baiter": 1.3,
}


def training_opponents_with_weights() -> list[tuple[type[Bot], float]]:
    """Return bot classes and their difficulty weights for training."""
    return [
        (cls, BOT_DIFFICULTY.get(name, 1.0))
        for name, cls in BOT_REGISTRY.items()
        if name not in _TRAINING_EXCLUDED
    ]
