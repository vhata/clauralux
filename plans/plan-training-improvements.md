# Plan: Richer Training Evaluation

## Why

The evolved bot currently trains against 7 hand-crafted bots on 3 maps (one static, two generated). That's a narrow evaluation surface. The bot can overfit to the specific quirks of those opponents — learning to exploit AggressiveBot's 100-tick wait or TurtleBot's refusal to fight early — rather than discovering genuinely strong play. The fitness signal (win + 0.3×draw) also collapses a lot of information into a single number.

## Problems

### 1. Opponent overfitting
All 7 opponents are deterministic. Same genome + same opponent + same map = same game every time (given the same seed). The evolved bot can memorise winning sequences rather than learning transferable strategy.

### 2. Map overfitting
Three map types (one fixed, two generated flavours) means the bot learns strategies that work on those specific geometries. The engine supports 4 map flavours (strategic, rush, chokepoint, swarm) — two are unused in training.

### 3. No self-play
The bot never faces anything that adapts. Hand-crafted bots are static targets. Self-play would force the evolved bot to handle opponents that improve alongside it.

### 4. Weak fitness signal
Win/draw/loss discards information. A bot that wins in 500 ticks by dominating is scored the same as one that barely survives to win at tick 9999. A bot that loses with 4 suns remaining scores the same as one eliminated in 200 ticks.

## Proposed Changes

### A. Expand the map pool
Use all 4 generated map flavours (strategic, rush, chokepoint, swarm) plus the fixed maps. Rotate seeds each generation so the bot never sees the same map twice across generations.

```python
MAP_FLAVOURS = ["strategic", "rush", "chokepoint", "swarm"]
# Per evaluation: cycle through flavours with generation-seeded RNG
```

### B. Add self-play
Include the previous generation's best genome as an opponent. The evolved bot now faces 8 opponents: 7 hand-crafted + 1 evolved (prior best). This creates an arms race without the instability of full self-play populations.

Later iteration: maintain a "hall of fame" — best genome from every Nth generation. Sample opponents from the hall of fame to prevent forgetting old counter-strategies.

### C. Add noisy opponents
Wrap hand-crafted bots in a noise layer that randomly delays or drops actions. This breaks the determinism of the evaluation — the evolved bot can't memorise sequences because the opponent varies slightly each game.

```python
class NoisyWrapper(Bot):
    def __init__(self, inner: Bot, drop_prob: float = 0.1, rng_seed: int = 0):
        ...
    def decide(self, view: GameView) -> list[Action]:
        actions = self._inner.decide(view)
        return [a for a in actions if self._rng.random() > self._drop_prob]
```

### D. Richer fitness signal
Replace the flat win/draw/loss scoring with a multi-component fitness:

```python
def score_game(result: GameResult, my_id: PlayerId, final_state: GameState) -> float:
    base = 1.0 if result.winner == my_id else (0.3 if result.is_draw else 0.0)

    # Bonus for winning quickly (normalised to [0, 0.2])
    speed_bonus = 0.2 * (1.0 - result.ticks / config.max_ticks) if result.winner == my_id else 0.0

    # Bonus for economic dominance at game end (normalised to [0, 0.1])
    my_suns = sum(1 for s in final_state.suns.values() if s.owner == my_id)
    total_suns = len(final_state.suns)
    territory_bonus = 0.1 * (my_suns / total_suns)

    return base + speed_bonus + territory_bonus
```

This rewards decisive victories over narrow ones and gives partial credit for strong positions even in losses.

### E. Vary seeds per generation
Currently the RNG seed is fixed from `TrainingConfig.seed`. Add generation-based seed variation so each generation sees different map layouts and opponent orderings:

```python
gen_seed = config.seed + generation * 1000
```

This prevents the population from overfitting to a single set of evaluation games.

## Implementation Order

1. Generation-varying seeds (smallest change, immediate benefit)
2. Expand map pool to all 4 flavours
3. Richer fitness signal (requires passing final GameState out of evaluation)
4. Self-play with previous-best genome
5. Noisy opponent wrappers
6. Hall of fame (later iteration)

## Risks

- **Richer fitness is harder to interpret.** The current win-rate metric is easy to understand. Multi-component fitness makes it harder to tell if training is improving. Mitigation: log both the raw win-rate and the composite fitness.
- **Self-play can destabilise training.** If the opponent changes every generation, fitness becomes non-stationary. Mitigation: only use previous-best (not current generation), and weight self-play games lower in the fitness calculation initially.
- **More maps/opponents = slower evaluation.** Each candidate plays more games. Mitigation: keep total games_per_eval constant but spread across more opponents/maps (fewer games per opponent rather than more total games).
