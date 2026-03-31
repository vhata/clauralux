//! Pure-Rust implementations of all hand-crafted bots for training.
//!
//! Each bot is a function: (state, config, player_id, &mut BotState) -> Vec<TAction>
//! These mirror the Python bots line-for-line for parity.

use std::collections::{HashMap, HashSet};

use crate::training::{TAction, TConfig, TGroup, TSun, TState, dist};

/// Persistent state for bots that need memory between ticks.
pub struct BotState {
    // BaiterBot state
    pub bait_target_owner: Option<i64>,
    pub bait_tick: Option<i64>,
    // RandomBot RNG (simple LCG)
    pub rng_state: u64,
}

impl BotState {
    pub fn new(seed: u64) -> Self {
        BotState {
            bait_target_owner: None,
            bait_tick: None,
            rng_state: seed.wrapping_mul(6364136223846793005).wrapping_add(1),
        }
    }

    fn next_rand(&mut self) -> u64 {
        self.rng_state = self.rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.rng_state >> 33
    }

    fn rand_float(&mut self) -> f64 {
        (self.next_rand() % 10000) as f64 / 10000.0
    }

    fn rand_range(&mut self, lo: i64, hi: i64) -> i64 {
        if hi <= lo { return lo; }
        lo + (self.next_rand() as i64 % (hi - lo + 1)).abs()
    }
}

// ── Helpers ──────────────────────────────────────────────────────────

fn my_suns<'a>(state: &'a TState, pid: i64) -> Vec<&'a TSun> {
    state.suns.values().filter(|s| s.owner == pid).collect()
}

fn non_friendly_suns<'a>(state: &'a TState, pid: i64) -> Vec<&'a TSun> {
    state.suns.values().filter(|s| s.owner != pid).collect()
}

fn enemy_suns<'a>(state: &'a TState, pid: i64) -> Vec<&'a TSun> {
    state.suns.values().filter(|s| s.owner != pid && s.owner != 0).collect()
}

fn neutral_suns<'a>(state: &'a TState) -> Vec<&'a TSun> {
    state.suns.values().filter(|s| s.owner == 0).collect()
}

fn total_available(suns: &[&TSun], reserve: f64) -> f64 {
    suns.iter().map(|s| (s.garrison - reserve).max(0.0)).sum()
}

fn send_from_all(suns: &[&TSun], target_id: i64, reserve: f64) -> Vec<TAction> {
    suns.iter()
        .filter_map(|s| {
            let avail = (s.garrison - reserve) as i64;
            if avail > 0 { Some(TAction::Send { source: s.id, target: target_id, count: avail }) } else { None }
        })
        .collect()
}

fn nearest_sun<'a>(from: &[&'a TSun], to: &TSun) -> Option<&'a TSun> {
    from.iter().min_by(|a, b| dist(a.x, a.y, to.x, to.y).partial_cmp(&dist(b.x, b.y, to.x, to.y)).unwrap()).copied()
}

// ── Bot implementations ─────────────────────────────────────────────

pub fn random_bot(state: &TState, _cfg: &TConfig, pid: i64, bot: &mut BotState) -> Vec<TAction> {
    if bot.rand_float() > 0.1 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }
    let sun_idx = (bot.next_rand() as usize) % mine.len();
    let sun = mine[sun_idx];
    if sun.garrison < 1.0 { return vec![]; }

    if bot.rand_float() < 0.2 {
        return vec![TAction::Upgrade { sun_id: sun.id }];
    }

    let targets = non_friendly_suns(state, pid);
    if targets.is_empty() { return vec![]; }
    let tgt = targets[(bot.next_rand() as usize) % targets.len()];
    let count = bot.rand_range(1, sun.garrison as i64);
    vec![TAction::Send { source: sun.id, target: tgt.id, count }]
}

pub fn aggressive_bot(state: &TState, _cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 100 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    let targets = non_friendly_suns(state, pid);
    if mine.is_empty() || targets.is_empty() { return vec![]; }

    let target = targets.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
    let avail = total_available(&mine, 2.0);
    if avail <= target.garrison { return vec![]; }
    send_from_all(&mine, target.id, 2.0)
}

pub fn expander_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 25 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }

    // Threat response
    let my_ids: HashSet<i64> = mine.iter().map(|s| s.id).collect();
    let mut threats: HashMap<i64, f64> = HashMap::new();
    for g in &state.groups {
        if g.owner != pid && my_ids.contains(&g.target_sun_id) {
            *threats.entry(g.target_sun_id).or_insert(0.0) += g.count as f64;
        }
    }
    if let Some((&worst_id, _)) = threats.iter()
        .filter(|(&sid, &incoming)| {
            let sun = state.suns.get(&sid).unwrap();
            incoming > sun.garrison
        })
        .max_by(|a, b| {
            let def_a = a.1 - state.suns.get(a.0).unwrap().garrison;
            let def_b = b.1 - state.suns.get(b.0).unwrap().garrison;
            def_a.partial_cmp(&def_b).unwrap()
        })
    {
        let deficit = threats[&worst_id] - state.suns.get(&worst_id).unwrap().garrison;
        let worst_sun = state.suns.get(&worst_id).unwrap();
        let safe: Vec<&TSun> = mine.iter()
            .filter(|s| s.id != worst_id && !threats.contains_key(&s.id) && s.garrison > 5.0)
            .copied().collect();
        if let Some(donor) = safe.iter().max_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()) {
            let send = ((donor.garrison - 3.0) as i64).min((deficit + 2.0) as i64);
            if send > 0 {
                return vec![TAction::Send { source: donor.id, target: worst_id, count: send }];
            }
        }
    }

    // Upgrade
    for sun in &mine {
        if sun.level < cfg.max_sun_level && sun.garrison >= 20.0 {
            return vec![TAction::Upgrade { sun_id: sun.id }];
        }
    }

    // Expand to nearest neutral
    let neutrals = neutral_suns(state);
    if !neutrals.is_empty() {
        if let Some(target) = nearest_to_any(&mine, &neutrals) {
            let avail = total_available(&mine, 3.0);
            if avail >= target.garrison * 0.8 {
                return send_from_all(&mine, target.id, 3.0);
            }
        }
    }

    // Attack weakest enemy
    let enemies = enemy_suns(state, pid);
    if !enemies.is_empty() {
        let target = enemies.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
        let avail = total_available(&mine, 3.0);
        if avail >= target.garrison * 1.2 {
            return send_from_all(&mine, target.id, 3.0);
        }
    }

    vec![]
}

fn nearest_to_any<'a>(mine: &[&TSun], targets: &[&'a TSun]) -> Option<&'a TSun> {
    targets.iter()
        .min_by(|a, b| {
            let da: f64 = mine.iter().map(|m| dist(m.x, m.y, a.x, a.y)).fold(f64::INFINITY, f64::min);
            let db: f64 = mine.iter().map(|m| dist(m.x, m.y, b.x, b.y)).fold(f64::INFINITY, f64::min);
            da.partial_cmp(&db).unwrap()
        })
        .copied()
}

pub fn turtle_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 30 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }

    // Upgrade
    for sun in &mine {
        if sun.level < cfg.max_sun_level {
            let cost_idx = (sun.level - 1) as usize;
            if cost_idx < cfg.upgrade_costs.len() && sun.garrison >= cfg.upgrade_costs[cost_idx] as f64 {
                return vec![TAction::Upgrade { sun_id: sun.id }];
            }
        }
    }

    // Early neutral grab
    let avg_level: f64 = mine.iter().map(|s| s.level as f64).sum::<f64>() / mine.len() as f64;
    if avg_level < 2.0 {
        let neutrals: Vec<&TSun> = neutral_suns(state).into_iter().filter(|s| s.garrison <= 15.0).collect();
        if let Some(target) = nearest_to_any(&mine, &neutrals) {
            let avail = total_available(&mine, 5.0);
            if avail > target.garrison {
                return send_from_all(&mine, target.id, 5.0);
            }
        }
        return vec![];
    }

    // Attack
    let targets = non_friendly_suns(state, pid);
    if targets.is_empty() { return vec![]; }
    let target = targets.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
    let total_garrison: f64 = mine.iter().map(|s| s.garrison).sum();
    if total_garrison < 40.0 { return vec![]; }
    send_from_all(&mine, target.id, 5.0)
}

pub fn rush_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 20 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }
    let targets = non_friendly_suns(state, pid);
    if targets.is_empty() { return vec![]; }

    let avail = total_available(&mine, 1.0);

    // Mid-game upgrade if no easy targets
    let easy: Vec<&&TSun> = targets.iter().filter(|t| t.garrison < avail * 0.8).collect();
    if easy.is_empty() {
        for sun in &mine {
            if sun.level < cfg.max_sun_level {
                let cost_idx = (sun.level - 1) as usize;
                if cost_idx < cfg.upgrade_costs.len() && sun.garrison >= cfg.upgrade_costs[cost_idx] as f64 {
                    return vec![TAction::Upgrade { sun_id: sun.id }];
                }
            }
        }
    }

    // Score targets: distance + garrison*5
    let mut best: Option<&TSun> = None;
    let mut best_score = f64::INFINITY;
    for t in &targets {
        if t.garrison > avail * 1.5 { continue; }
        let min_d = mine.iter().map(|m| dist(m.x, m.y, t.x, t.y)).fold(f64::INFINITY, f64::min);
        let score = min_d + t.garrison * 5.0;
        if score < best_score { best_score = score; best = Some(t); }
    }

    let target = best.unwrap_or_else(|| {
        targets.iter().min_by(|a, b| {
            let da = mine.iter().map(|m| dist(m.x, m.y, a.x, a.y)).fold(f64::INFINITY, f64::min);
            let db = mine.iter().map(|m| dist(m.x, m.y, b.x, b.y)).fold(f64::INFINITY, f64::min);
            da.partial_cmp(&db).unwrap()
        }).unwrap()
    });

    if avail < target.garrison * 0.6 { return vec![]; }
    send_from_all(&mine, target.id, 1.0)
}

pub fn sniper_bot(state: &TState, _cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 60 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }

    let enemies = enemy_suns(state, pid);
    if enemies.is_empty() {
        // Mop up neutrals
        let neutrals = neutral_suns(state);
        if neutrals.is_empty() { return vec![]; }
        let target = neutrals.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
        let avail = total_available(&mine, 3.0);
        if avail > target.garrison { return send_from_all(&mine, target.id, 3.0); }
        return vec![];
    }

    // Find weakest player by total units (garrison + in-flight)
    let mut player_strength: HashMap<i64, f64> = HashMap::new();
    for s in &enemies {
        *player_strength.entry(s.owner).or_insert(0.0) += s.garrison;
    }
    for g in &state.groups {
        if g.owner != pid && g.owner != 0 {
            *player_strength.entry(g.owner).or_insert(0.0) += g.count as f64;
        }
    }

    let weakest_player = *player_strength.iter()
        .min_by(|a, b| a.1.partial_cmp(b.1).unwrap())
        .unwrap().0;

    // Target that player's weakest sun
    let target = enemies.iter()
        .filter(|s| s.owner == weakest_player)
        .min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap())
        .unwrap();

    let avail = total_available(&mine, 3.0);
    if avail > target.garrison { return send_from_all(&mine, target.id, 3.0); }
    vec![]
}

pub fn opportunist_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 30 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }
    let targets = non_friendly_suns(state, pid);
    if targets.is_empty() { return vec![]; }

    let avail = total_available(&mine, 3.0);

    // Score: garrison + distance*0.05
    let mut scored: Vec<(f64, &TSun)> = targets.iter().map(|t| {
        let min_d = mine.iter().map(|m| dist(m.x, m.y, t.x, t.y)).fold(f64::INFINITY, f64::min);
        (t.garrison + min_d * 0.05, *t)
    }).collect();
    scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

    let (_, best) = scored[0];
    if best.garrison < avail * 0.8 {
        return send_from_all(&mine, best.id, 3.0);
    }

    // Upgrade instead
    for sun in &mine {
        if sun.level < cfg.max_sun_level && sun.garrison >= 20.0 {
            return vec![TAction::Upgrade { sun_id: sun.id }];
        }
    }
    vec![]
}

pub fn swarm_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 15 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }
    let targets = non_friendly_suns(state, pid);
    if targets.is_empty() { return vec![]; }

    let weakest = targets.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
    let send_size = 3i64.max((weakest.garrison * 0.35) as i64);

    let ready: Vec<&TSun> = mine.iter().filter(|s| s.garrison > (send_size + 2) as f64).copied().collect();
    if ready.is_empty() {
        // Upgrade fallback
        for sun in &mine {
            if sun.level < cfg.max_sun_level {
                let ci = (sun.level - 1) as usize;
                if ci < cfg.upgrade_costs.len() && sun.garrison >= cfg.upgrade_costs[ci] as f64 {
                    return vec![TAction::Upgrade { sun_id: sun.id }];
                }
            }
        }
        return vec![];
    }

    let total_sendable = ready.len() as i64 * send_size;
    if weakest.garrison <= total_sendable as f64 * 0.7 {
        // Concentrate
        let needed = (weakest.garrison * 1.3) as i64 + 1;
        let mut sorted = ready.clone();
        sorted.sort_by(|a, b| dist(a.x, a.y, weakest.x, weakest.y).partial_cmp(&dist(b.x, b.y, weakest.x, weakest.y)).unwrap());
        let mut actions = Vec::new();
        let mut sent = 0i64;
        for sun in sorted {
            let amount = send_size.min((sun.garrison - 2.0) as i64);
            if amount > 0 {
                actions.push(TAction::Send { source: sun.id, target: weakest.id, count: amount });
                sent += amount;
            }
            if sent >= needed { break; }
        }
        if !actions.is_empty() { return actions; }
    }

    // Spread
    let weak_targets: Vec<&TSun> = {
        let filtered: Vec<&TSun> = targets.iter().filter(|t| t.garrison <= (send_size * 4) as f64).copied().collect();
        if filtered.is_empty() { targets.iter().copied().collect() } else { filtered }
    };

    let mut actions = Vec::new();
    for sun in &ready {
        let tgt = weak_targets.iter().min_by(|a, b| dist(sun.x, sun.y, a.x, a.y).partial_cmp(&dist(sun.x, sun.y, b.x, b.y)).unwrap()).unwrap();
        let amount = send_size.min((sun.garrison - 2.0) as i64);
        if amount >= 3 {
            actions.push(TAction::Send { source: sun.id, target: tgt.id, count: amount });
        }
    }
    actions
}

pub fn coordinator_bot(state: &TState, _cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 80 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    let targets = non_friendly_suns(state, pid);
    if mine.is_empty() || targets.is_empty() { return vec![]; }

    let ready: Vec<&TSun> = mine.iter().filter(|s| s.garrison >= 12.0).copied().collect();
    if ready.is_empty() { return vec![]; }

    let mut sorted_targets: Vec<&TSun> = targets;
    sorted_targets.sort_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap());

    let mut actions = Vec::new();
    let mut claimed: HashSet<i64> = HashSet::new();

    for sun in &ready {
        // Find nearest unclaimed target
        let target = sorted_targets.iter()
            .filter(|t| !claimed.contains(&t.id))
            .min_by(|a, b| dist(sun.x, sun.y, a.x, a.y).partial_cmp(&dist(sun.x, sun.y, b.x, b.y)).unwrap());
        if let Some(t) = target {
            let send = (sun.garrison - 3.0) as i64;
            if send > 0 {
                actions.push(TAction::Send { source: sun.id, target: t.id, count: send });
                claimed.insert(t.id);
            }
        }
    }
    actions
}

pub fn reactive_bot(state: &TState, _cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 25 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }

    // Threat detection
    let my_ids: HashSet<i64> = mine.iter().map(|s| s.id).collect();
    let mut threats: HashMap<i64, f64> = HashMap::new();
    for g in &state.groups {
        if g.owner != pid && my_ids.contains(&g.target_sun_id) {
            *threats.entry(g.target_sun_id).or_insert(0.0) += g.count as f64;
        }
    }

    // Reinforce most threatened sun
    if let Some((&worst_id, &incoming)) = threats.iter()
        .max_by(|a, b| {
            let def_a = a.1 - state.suns.get(a.0).unwrap().garrison;
            let def_b = b.1 - state.suns.get(b.0).unwrap().garrison;
            def_a.partial_cmp(&def_b).unwrap()
        })
    {
        let deficit = incoming - state.suns.get(&worst_id).unwrap().garrison;
        if deficit > 0.0 {
            // Find safest donor (no threats, most garrison)
            let donor = mine.iter()
                .filter(|s| s.id != worst_id && !threats.contains_key(&s.id) && s.garrison > 5.0)
                .max_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap());
            if donor.is_none() {
                // Fallback: any sun with garrison
                let donor = mine.iter()
                    .filter(|s| s.id != worst_id && s.garrison > 5.0)
                    .max_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap());
                if let Some(d) = donor {
                    let send = ((d.garrison - 5.0) as i64).min((deficit + 5.0) as i64);
                    if send > 0 {
                        return vec![TAction::Send { source: d.id, target: worst_id, count: send }];
                    }
                }
            } else if let Some(d) = donor {
                let send = ((d.garrison - 5.0) as i64).min((deficit + 5.0) as i64);
                if send > 0 {
                    return vec![TAction::Send { source: d.id, target: worst_id, count: send }];
                }
            }
        }
    }

    // Attack with 2x advantage
    let enemies = enemy_suns(state, pid);
    if enemies.is_empty() {
        let neutrals = neutral_suns(state);
        if let Some(target) = neutrals.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()) {
            let avail = total_available(&mine, 5.0);
            if avail >= target.garrison * 2.0 {
                return send_from_all(&mine, target.id, 5.0);
            }
        }
        return vec![];
    }
    let target = enemies.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
    let avail = total_available(&mine, 5.0);
    if avail >= target.garrison * 2.0 {
        return send_from_all(&mine, target.id, 5.0);
    }
    vec![]
}

pub fn economic_bot(state: &TState, cfg: &TConfig, pid: i64, _bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 35 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }

    // Grab nearest neutral
    let neutrals = neutral_suns(state);
    if !neutrals.is_empty() {
        if let Some(target) = nearest_to_any(&mine, &neutrals) {
            let needed = target.garrison + 2.0;
            let avail = total_available(&mine, 3.0);
            if avail >= needed {
                return send_from_all(&mine, target.id, 3.0);
            }
        }
    }

    // Upgrade lowest-level sun
    let mut upgradeable: Vec<&TSun> = mine.iter()
        .filter(|s| s.level < cfg.max_sun_level)
        .copied().collect();
    upgradeable.sort_by(|a, b| a.level.cmp(&b.level).then(b.garrison.partial_cmp(&a.garrison).unwrap()));
    for sun in upgradeable {
        let ci = (sun.level - 1) as usize;
        if ci < cfg.upgrade_costs.len() && sun.garrison >= cfg.upgrade_costs[ci] as f64 {
            return vec![TAction::Upgrade { sun_id: sun.id }];
        }
    }

    // Attack enemy's highest-level sun (deny economy)
    let enemies = enemy_suns(state, pid);
    if !enemies.is_empty() {
        let target = enemies.iter()
            .max_by(|a, b| a.level.cmp(&b.level).then(a.garrison.partial_cmp(&b.garrison).unwrap()))
            .unwrap();
        let avail = total_available(&mine, 3.0);
        if avail > target.garrison {
            return send_from_all(&mine, target.id, 3.0);
        }
    }
    vec![]
}

pub fn baiter_bot(state: &TState, _cfg: &TConfig, pid: i64, bot: &mut BotState) -> Vec<TAction> {
    if state.tick % 40 != 0 { return vec![]; }
    let mine = my_suns(state, pid);
    if mine.is_empty() { return vec![]; }
    let enemies = enemy_suns(state, pid);
    if enemies.is_empty() { return vec![]; }

    // Check if we're in follow-up window
    if let (Some(bait_owner), Some(bait_tick)) = (bot.bait_target_owner, bot.bait_tick) {
        if state.tick - bait_tick < 200 {
            // Strike weakest sun of the baited player
            let strike_targets: Vec<&TSun> = enemies.iter().filter(|s| s.owner == bait_owner).copied().collect();
            if let Some(target) = strike_targets.iter().min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()) {
                let avail = total_available(&mine, 3.0);
                if avail > target.garrison {
                    bot.bait_target_owner = None;
                    bot.bait_tick = None;
                    return send_from_all(&mine, target.id, 3.0);
                }
            }
            return vec![];
        }
        // Window expired, reset
        bot.bait_target_owner = None;
        bot.bait_tick = None;
    }

    // Send bait: 2 units to the most distant enemy sun
    let farthest = enemies.iter().max_by(|a, b| {
        let da = mine.iter().map(|m| dist(m.x, m.y, a.x, a.y)).fold(0.0_f64, f64::max);
        let db = mine.iter().map(|m| dist(m.x, m.y, b.x, b.y)).fold(0.0_f64, f64::max);
        da.partial_cmp(&db).unwrap()
    }).unwrap();

    let sender = mine.iter().max_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap()).unwrap();
    if sender.garrison > 5.0 {
        bot.bait_target_owner = Some(farthest.owner);
        bot.bait_tick = Some(state.tick);
        return vec![TAction::Send { source: sender.id, target: farthest.id, count: 2 }];
    }
    vec![]
}

/// Dispatch to the appropriate bot by name.
pub fn run_bot(name: &str, state: &TState, cfg: &TConfig, pid: i64, bot_state: &mut BotState) -> Vec<TAction> {
    match name {
        "random" => random_bot(state, cfg, pid, bot_state),
        "aggressive" => aggressive_bot(state, cfg, pid, bot_state),
        "expander" => expander_bot(state, cfg, pid, bot_state),
        "turtle" => turtle_bot(state, cfg, pid, bot_state),
        "rush" => rush_bot(state, cfg, pid, bot_state),
        "sniper" => sniper_bot(state, cfg, pid, bot_state),
        "opportunist" => opportunist_bot(state, cfg, pid, bot_state),
        "swarm" => swarm_bot(state, cfg, pid, bot_state),
        "coordinator" => coordinator_bot(state, cfg, pid, bot_state),
        "reactive" => reactive_bot(state, cfg, pid, bot_state),
        "economic" => economic_bot(state, cfg, pid, bot_state),
        "baiter" => baiter_bot(state, cfg, pid, bot_state),
        _ => vec![],
    }
}
