# Future Improvements

## Neural Bot Enhancements

### Richer Input Features
The current 12 inputs are bare bones. Adding more would let the net make smarter decisions:
- Per-sun features: distance to nearest neutral, distance to nearest enemy
- Garrison trends: is my total garrison growing or shrinking over the last 200 ticks
- Opponent behavior: are they massing units near my weakest sun, are they upgrading
- Map awareness: how contested is the center, are there isolated suns worth grabbing
- Could go from 12 to 25-30 features without major architectural changes

### Deeper Network
One hidden layer with 32 neurons is a toy. Adding a second hidden layer (12→32→32→29) would let it learn more complex conditional strategies like "if losing AND opponent is turtling, rush before they snowball." Simple code change, adds ~1000 weights.

### Recurrent Memory
Currently the net is completely memoryless — every tick it sees a fresh snapshot with no history. It can't learn patterns like "the opponent has been turtling for 500 ticks, they're about to attack" or "I tried attacking that sun twice and got repelled, try somewhere else." Even a simple carry-forward hidden state between ticks would help massively. This is probably the single biggest unlock.

### Coevolution
Instead of one population evolving against fixed opponents, maintain two or more populations of neural bots that evolve against each other. Creates a genuine arms race where strategies and counter-strategies emerge organically, instead of optimising against static targets.

### Gradient-Based Training (PPO/RL)
For networks with 2000+ weights, evolutionary search becomes sample-inefficient. Reinforcement learning (e.g., PPO) would converge much faster. Requires a reward signal and a differentiable framework — significant infrastructure work, but would unlock much larger networks.

### Population-Based Training (PBT)
Instead of fixed training hyperparameters (sigma, mutation rate, population size), evolve the hyperparameters alongside the network weights. Each individual carries its own sigma/mutation config, and successful configs propagate with successful genomes.
