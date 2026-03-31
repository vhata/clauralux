# Performance TODO

Training speed improvements, ordered by expected impact.

## Done

- [x] **Rust game engine** — tick loop, movement, combat, production all in Rust (~10x vs pure Python)
- [x] **Rust evolved bot heuristic** — `run_training_game()` runs evolved-vs-evolved with zero Python round-trips (16x faster, 0.45ms/game)
- [x] **NumPy vectorized MLP forward pass** — neural bot uses NumPy instead of scalar Python math
- [x] **Parity tests** — catch drift between Python and Rust evolved bot implementations
- [x] **Rust MLP forward pass for neural training** — `run_neural_training_game()` with feature extraction, recurrent MLP, and output decoding all in Rust (25x faster, 18.5ms/game)

## High Impact
- [ ] **Port opponent bots to Rust** — the 12 hand-crafted bots are simple heuristics (50-100 lines each). Porting them would let ALL training games use the Rust path, not just evolved-vs-evolved. Currently most training time is still spent on Python opponents.
- [ ] **Parallel game evaluation within workers** — each ProcessPoolExecutor worker plays games sequentially. Could use Rust-level threading (rayon) to run multiple games per worker since pure-Rust games don't need the GIL.

## Medium Impact

- [ ] **Adaptive evaluation** — screen candidates with fewer games first (e.g. 10), only run the full 40 games on the top 50%. Halves total games for weak candidates.
- [ ] **Reduce max_ticks for training** — many games are decided by tick 5000. Using 7000 instead of 10000 would cut ~30% of tick processing for long draws.
- [ ] **Lazy GameView creation** — Python path creates a full GameView snapshot every decision tick even when the bot returns []. Could defer view creation until the bot actually reads it.
- [ ] **Cached feature extraction** — neural bot recomputes all 20 features from scratch each tick. Some (sun count, garrison) change incrementally; could maintain running totals.

## Low Impact (diminishing returns)

- [ ] **SIMD for unit position updates** — vectorize the movement loop for games with 1000+ unit groups
- [ ] **Spatial hash for arrival detection** — O(1) collision checks instead of O(n), matters at >5000 groups
- [ ] **Pre-allocate Rust vectors** — avoid reallocation in hot loops (groups, arrived, remaining)
- [ ] **Reduce `clone()` in Rust tick** — some sun/group clones could be avoided with lifetime tricks

## Not Worth It

- **GPU acceleration** — game is fundamentally sequential (tick-by-tick); parallelism is across games not within them
- **Full RL (PPO/A3C)** — requires differentiable framework rewrite, evolutionary search works well enough for the genome sizes involved
- **Persistent data structures for undo** — no use case for rewinding game state during training
