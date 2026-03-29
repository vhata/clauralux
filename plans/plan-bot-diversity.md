# Plan: More Diverse Bot Archetypes

## Why

The 7 hand-crafted bots (excluding Passive and Random) share a common pattern: accumulate units at suns, pick a target, send everything. They differ in timing and target selection, but the strategic *shape* is the same — build up, attack, repeat. None of them do anything that requires the evolved bot to learn genuinely different counter-strategies.

This limits what the evolved bot can discover. If every opponent is some flavour of "wait then rush", the evolved bot just needs to learn the right timing window. It never has to deal with coordinated attacks, deception, economic strangulation, or defensive play.

## What's Missing

### Multi-front pressure
No bot attacks from multiple directions simultaneously. Every bot picks one target and sends everything at it. A bot that coordinates attacks on two suns at once would force the evolved bot to learn defensive triage — which sun to reinforce, which to sacrifice.

### Economic denial
No bot targets the opponent's economy specifically. Sniping high-level suns (even if they're well-defended) to crash production is a valid strategy that nothing currently tests.

### Defensive/reactive play
No hand-crafted bot reacts to incoming threats. They all make decisions in isolation. A bot that pulls back when it sees incoming units, or reinforces threatened suns, would test whether the evolved bot can handle an opponent that doesn't just walk into attacks.

### Sacrifice/bait
No bot deliberately sacrifices a sun to draw the opponent out of position. Send a small force at a distant target to pull the defender's garrison, then hit their weakened home suns.

## Proposed New Bots

### 1. CoordinatorBot
**Strategy:** Multi-front simultaneous attacks.

Accumulates across multiple suns, then launches attacks at 2-3 enemy suns simultaneously on the same tick. Forces the opponent to split defensive attention.

```
- Wait until 3+ suns have garrison > threshold
- Identify 2-3 enemy targets with lowest garrison
- Send from nearest sun to each target simultaneously
- Intent: "Coordinating strike on suns 3, 7, 12"
```

**What it tests:** Can the evolved bot handle distributed pressure? Does it know how to triage?

### 2. EconomicBot
**Strategy:** Production superiority through aggressive upgrading and denial.

Upgrades its own suns to max level as fast as possible, then targets the opponent's highest-level suns specifically. Doesn't care about easy kills — wants to destroy the opponent's economy.

```
- Phase 1: Grab nearest neutrals, upgrade everything to max
- Phase 2: Target enemy suns sorted by level (highest first), not garrison
- Willing to overspend on attacks against high-level targets
- Intent: "Targeting level 3 sun — denying production"
```

**What it tests:** Does the evolved bot protect its high-value suns? Does it understand that losing a level-3 sun is worse than losing a level-1?

### 3. ReactiveBot
**Strategy:** Defensive play that responds to opponent actions.

Watches incoming unit groups and adjusts. Reinforces threatened suns, pulls garrison from suns that aren't under threat, only attacks when it has a clear numbers advantage AND no incoming threats.

```
- Every tick: scan incoming enemy unit groups
- If sun is threatened: reinforce from nearest safe sun
- If no threats: look for attack opportunities (only when total_available > 2× target garrison)
- Never leaves a sun with < reserve garrison
- Intent: "Reinforcing sun 4 (12 incoming), holding"
```

**What it tests:** Can the evolved bot break through a defensive opponent? Does it need to learn feints or overwhelming force concentration?

### 4. BaiterBot
**Strategy:** Deliberate sacrifice to create openings.

Sends small, cheap attacks at distant targets to draw out the opponent's garrison, then hits the weakened suns hard.

```
- Phase 1: Send 1-2 units at a distant enemy sun (the bait)
- Phase 2: Wait for opponent to reinforce the baited sun or counter-attack
- Phase 3: Hit the sun they pulled garrison FROM
- Intent: "Baiting sun 5, waiting for response"
```

**What it tests:** Can the evolved bot avoid overreacting to small threats? Does it know when NOT to reinforce?

### 5. SwarmBot
**Strategy:** Many small attacks rather than few large ones.

Never accumulates — sends small groups constantly from every sun at the nearest target. Death by a thousand cuts. Overwhelms through action volume rather than force concentration.

```
- Every decision tick: from every sun with garrison > 3, send 2-3 units at nearest enemy/neutral
- Never holds back, never upgrades
- Intent: "Swarming — 6 groups in flight"
```

**What it tests:** Can the evolved bot handle constant low-level pressure from multiple directions? Does its overkill_aversion parameter help or hurt against tiny attacks?

## Implementation Notes

- Each bot is a single file in `src/clauralux/bots/`, inheriting from `Bot`
- Register in `BOT_REGISTRY` — appears in menu automatically
- Add to `OPPONENT_BOTS` in `trainer.py` to include in training evaluation
- Keep decision logic simple and readable — these are training opponents, not meant to be optimal
- Set `self._intent` strings for HUD debugging

## Implementation Order

1. **SwarmBot** — simplest to implement, tests a genuinely different attack pattern
2. **CoordinatorBot** — straightforward multi-target logic, high training value
3. **ReactiveBot** — requires scanning `view.unit_groups` for incoming threats, moderate complexity
4. **EconomicBot** — needs target-by-level sorting, otherwise simple
5. **BaiterBot** — most complex (needs state across ticks to track bait/response cycle), implement last

## Impact on Training

Adding 5 new opponents to the training set means the evolved bot faces 12 opponents instead of 7. To keep evaluation time constant, reduce games-per-opponent rather than increasing total games. The diversity of opponent strategies matters more than the sample size per opponent.

These bots should push the evolved bot's parameters into more interesting regions — particularly the defensive parameters (threat_response, reinforce_own, defensive_garrison_threshold) that probably aren't getting much selection pressure right now because no opponent tests them.
