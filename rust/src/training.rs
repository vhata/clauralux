//! Pure-Rust training game runner.
//!
//! Runs a complete game with the evolved bot heuristic without any
//! Python/Rust boundary crossings. The bot logic is a direct port of
//! the Python `EvolvedBot.decide()`.

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

// ── Internal game structures (no Py<> wrappers) ──────────────────────

#[derive(Clone)]
struct TSun {
    id: i64,
    x: f64,
    y: f64,
    owner: i64,
    level: i64,
    garrison: f64,
    production_ticks: i64,
}

#[derive(Clone)]
struct TGroup {
    owner: i64,
    count: i64,
    x: f64,
    y: f64,
    target_sun_id: i64,
    vx: f64,
    vy: f64,
}

#[derive(Clone)]
struct TConfig {
    production_interval: i64,
    production_per_level: i64,
    max_sun_level: i64,
    upgrade_costs: Vec<i64>,
    capture_level_reset: Option<i64>,
    unit_speed: f64,
    attack_ratio: f64,
    decision_interval: i64,
    max_ticks: Option<i64>,
}

struct TState {
    suns: HashMap<i64, TSun>,
    groups: Vec<TGroup>,
    players: Vec<i64>,
    tick: i64,
    winner: Option<i64>,
    eliminated: HashSet<i64>,
}

enum TAction {
    Send { source: i64, target: i64, count: i64 },
    Upgrade { sun_id: i64 },
}

// ── Distance helper ──────────────────────────────────────────────────

fn dist(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    ((x2 - x1).powi(2) + (y2 - y1).powi(2)).sqrt()
}

fn direction(x1: f64, y1: f64, x2: f64, y2: f64) -> (f64, f64) {
    let d = dist(x1, y1, x2, y2);
    if d == 0.0 {
        (0.0, 0.0)
    } else {
        ((x2 - x1) / d, (y2 - y1) / d)
    }
}

// ── Game tick logic (mirrors game.rs) ────────────────────────────────

fn process_actions(state: &mut TState, cfg: &TConfig, player_id: i64, actions: &[TAction]) {
    for action in actions {
        match action {
            TAction::Send { source, target, count } => {
                if source == target || *count <= 0 {
                    continue;
                }
                let (src_x, src_y, actual) = {
                    let Some(sun) = state.suns.get_mut(source) else { continue };
                    if sun.owner != player_id { continue; }
                    let actual = (*count).min(sun.garrison as i64);
                    if actual <= 0 { continue; }
                    sun.garrison -= actual as f64;
                    (sun.x, sun.y, actual)
                };
                let Some(tgt) = state.suns.get(target) else { continue };
                let (dx, dy) = direction(src_x, src_y, tgt.x, tgt.y);
                state.groups.push(TGroup {
                    owner: player_id,
                    count: actual,
                    x: src_x,
                    y: src_y,
                    target_sun_id: *target,
                    vx: dx * cfg.unit_speed,
                    vy: dy * cfg.unit_speed,
                });
            }
            TAction::Upgrade { sun_id } => {
                let Some(sun) = state.suns.get_mut(sun_id) else { continue };
                if sun.owner != player_id || sun.level >= cfg.max_sun_level {
                    continue;
                }
                let cost_idx = (sun.level - 1) as usize;
                if cost_idx >= cfg.upgrade_costs.len() { continue; }
                let cost = cfg.upgrade_costs[cost_idx];
                if (sun.garrison as i64) < cost { continue; }
                sun.garrison -= cost as f64;
                sun.level += 1;
            }
        }
    }
}

fn move_groups(state: &mut TState) {
    for g in &mut state.groups {
        g.x += g.vx;
        g.y += g.vy;
    }
}

fn resolve_arrivals(state: &mut TState, cfg: &TConfig) {
    let mut remaining = Vec::new();
    let mut arrived: Vec<(i64, i64, i64)> = Vec::new();

    for g in &state.groups {
        if let Some(tgt) = state.suns.get(&g.target_sun_id) {
            let d = dist(g.x, g.y, tgt.x, tgt.y);
            if d <= cfg.unit_speed {
                arrived.push((g.owner, g.count, g.target_sun_id));
            } else {
                remaining.push(g.clone());
            }
        }
    }
    state.groups = remaining;

    for (owner, count, target_id) in arrived {
        let Some(tgt) = state.suns.get_mut(&target_id) else { continue };
        if owner == tgt.owner {
            tgt.garrison += count as f64;
        } else {
            let damage = count as f64 * cfg.attack_ratio;
            tgt.garrison -= damage;
            if tgt.garrison <= 0.0 {
                let remaining_units = tgt.garrison.abs() / cfg.attack_ratio;
                tgt.owner = owner;
                tgt.garrison = remaining_units;
                tgt.production_ticks = 0;
                if let Some(reset) = cfg.capture_level_reset {
                    tgt.level = reset;
                }
            }
        }
    }
}

fn produce_units(state: &mut TState, cfg: &TConfig) {
    for sun in state.suns.values_mut() {
        if sun.owner == 0 { continue; }
        sun.production_ticks += 1;
        let prod_rate = (sun.level * cfg.production_per_level).max(1);
        let ticks_per_unit = cfg.production_interval / prod_rate;
        if ticks_per_unit > 0 && sun.production_ticks >= ticks_per_unit {
            sun.garrison += 1.0;
            sun.production_ticks = 0;
        }
    }
}

fn check_win(state: &mut TState, cfg: &TConfig) {
    let players = state.players.clone();
    for &pid in &players {
        if state.eliminated.contains(&pid) { continue; }
        let owns = state.suns.values().any(|s| s.owner == pid);
        let has_groups = state.groups.iter().any(|g| g.owner == pid);
        if !owns && !has_groups {
            state.eliminated.insert(pid);
        }
    }
    let active: Vec<i64> = players.iter().filter(|p| !state.eliminated.contains(p)).copied().collect();
    if active.len() == 1 {
        state.winner = Some(active[0]);
    } else if active.is_empty() {
        state.winner = Some(0);
    } else if let Some(max_ticks) = cfg.max_ticks {
        if state.tick >= max_ticks {
            state.winner = Some(0);
        }
    }
}

// ── Evolved bot heuristic (mirrors evolved.py) ──────────────────────

const NUM_PHASE_PARAMS: usize = 25;

struct EvolvedParams {
    phases: [Vec<f64>; 3],
    transitions: [f64; 2],
}

impl EvolvedParams {
    fn from_genome(genome: &[f64]) -> Self {
        let mut phases = [Vec::new(), Vec::new(), Vec::new()];
        for i in 0..3 {
            let start = i * NUM_PHASE_PARAMS;
            phases[i] = genome[start..start + NUM_PHASE_PARAMS].to_vec();
        }
        let t_start = 3 * NUM_PHASE_PARAMS;
        EvolvedParams {
            phases,
            transitions: [genome[t_start], genome[t_start + 1]],
        }
    }

    fn phase_for_tick(&self, tick: i64) -> usize {
        let t = tick as f64;
        if t < self.transitions[0] {
            0
        } else if t < self.transitions[1] {
            1
        } else {
            2
        }
    }

    fn g(&self, phase: usize, idx: usize) -> f64 {
        self.phases[phase][idx]
    }

    fn gi(&self, phase: usize, idx: usize) -> i64 {
        (self.phases[phase][idx] as i64).max(1)
    }
}

// Parameter indices (must match PARAM_SPECS order in genome.py)
const P_W_GARRISON: usize = 0;
const P_W_DISTANCE: usize = 1;
const P_W_LEVEL: usize = 2;
const P_W_NEUTRAL_BONUS: usize = 3;
const P_W_ENEMY_BONUS: usize = 4;
const P_W_INCOMING_FRIENDLY: usize = 5;
const P_RESERVE_PER_SUN: usize = 6;
const P_MIN_FORCE_RATIO: usize = 7;
const P_SEND_FRACTION: usize = 8;
const P_CONCENTRATE_VS_SPLIT: usize = 9;
const P_MAX_TARGETS_PER_TICK: usize = 10;
const P_OVERKILL_AVERSION: usize = 11;
const P_UPGRADE_THRESHOLD: usize = 12;
const P_UPGRADE_VS_ATTACK: usize = 13;
const P_MAX_UPGRADE_LEVEL: usize = 14;
const P_UPGRADE_WHEN_NO_TARGETS: usize = 15;
const P_ECO_PHASE_DURATION: usize = 16;
const P_ACT_INTERVAL: usize = 17;
const P_EARLY_AGGRESSION: usize = 18;
const P_PATIENCE: usize = 19;
const P_NEAREST_SUN_WEIGHT: usize = 20;
const P_REINFORCE_OWN: usize = 21;
const P_DEFENSIVE_GARRISON_THRESHOLD: usize = 22;
const P_W_ENEMY_INCOMING: usize = 23;
const P_THREAT_RESPONSE: usize = 24;

fn evolved_decide(
    state: &TState,
    cfg: &TConfig,
    params: &EvolvedParams,
    player_id: i64,
) -> Vec<TAction> {
    let phase = params.phase_for_tick(state.tick);

    let act_interval = params.gi(phase, P_ACT_INTERVAL);
    if state.tick % act_interval != 0 {
        return vec![];
    }

    let my_suns: Vec<&TSun> = state.suns.values().filter(|s| s.owner == player_id).collect();
    if my_suns.is_empty() {
        return vec![];
    }

    let reserve = params.g(phase, P_RESERVE_PER_SUN);
    let mut available: HashMap<i64, f64> = HashMap::new();
    let mut total_available: f64 = 0.0;
    for s in &my_suns {
        let a = (s.garrison - reserve).max(0.0);
        available.insert(s.id, a);
        total_available += a;
    }

    if total_available <= 0.0 {
        return vec![];
    }

    // 1. Threat response
    if let Some(actions) = handle_threats(state, &my_suns, &available, params, phase) {
        return actions;
    }

    // 2. Reinforce
    if let Some(actions) = handle_reinforce(state, &my_suns, &available, params, phase) {
        return actions;
    }

    // 3. Upgrade
    if let Some(actions) = handle_upgrade(state, cfg, &my_suns, total_available, params, phase, player_id) {
        return actions;
    }

    // 4. Attack
    handle_attack(state, cfg, &my_suns, &mut available.clone(), total_available, params, phase, player_id)
}

fn handle_threats(
    state: &TState,
    my_suns: &[&TSun],
    available: &HashMap<i64, f64>,
    params: &EvolvedParams,
    phase: usize,
) -> Option<Vec<TAction>> {
    let threat_response = params.g(phase, P_THREAT_RESPONSE);
    if threat_response < 0.3 {
        return None;
    }

    let w_incoming = params.g(phase, P_W_ENEMY_INCOMING);
    let my_ids: HashSet<i64> = my_suns.iter().map(|s| s.id).collect();

    let mut worst_id: Option<i64> = None;
    let mut worst_deficit = 0.0f64;

    for sun in my_suns {
        let incoming: f64 = state.groups.iter()
            .filter(|g| !my_ids.contains(&g.owner) && g.target_sun_id == sun.id)
            .map(|g| g.count as f64 * w_incoming)
            .sum();
        let deficit = incoming - sun.garrison;
        if deficit > worst_deficit {
            worst_deficit = deficit;
            worst_id = Some(sun.id);
        }
    }

    let worst_id = worst_id?;

    // Find nearest source with spare units.
    let worst_sun = my_suns.iter().find(|s| s.id == worst_id)?;
    let mut best_src: Option<i64> = None;
    let mut best_dist = f64::INFINITY;
    for sun in my_suns {
        if sun.id == worst_id { continue; }
        let a = *available.get(&sun.id).unwrap_or(&0.0);
        if a <= 0.0 { continue; }
        let d = dist(sun.x, sun.y, worst_sun.x, worst_sun.y);
        if d < best_dist {
            best_dist = d;
            best_src = Some(sun.id);
        }
    }

    let src_id = best_src?;
    let send_frac = params.g(phase, P_SEND_FRACTION);
    let send = (*available.get(&src_id).unwrap_or(&0.0) * send_frac) as i64;
    if send <= 0 { return None; }

    Some(vec![TAction::Send { source: src_id, target: worst_id, count: send }])
}

fn handle_reinforce(
    state: &TState,
    my_suns: &[&TSun],
    available: &HashMap<i64, f64>,
    params: &EvolvedParams,
    phase: usize,
) -> Option<Vec<TAction>> {
    if my_suns.len() < 2 {
        return None;
    }

    let reinforce_prob = params.g(phase, P_REINFORCE_OWN);
    let threshold = params.g(phase, P_DEFENSIVE_GARRISON_THRESHOLD);

    if (state.tick * 7) % 100 >= (reinforce_prob * 100.0) as i64 {
        return None;
    }

    let weakest = my_suns.iter()
        .filter(|s| s.garrison < threshold)
        .min_by(|a, b| a.garrison.partial_cmp(&b.garrison).unwrap())?;

    let strongest = my_suns.iter()
        .filter(|s| s.id != weakest.id)
        .max_by(|a, b| {
            let aa = available.get(&a.id).unwrap_or(&0.0);
            let bb = available.get(&b.id).unwrap_or(&0.0);
            aa.partial_cmp(bb).unwrap()
        })?;

    let avail = *available.get(&strongest.id).unwrap_or(&0.0);
    if avail <= 0.0 { return None; }

    let send_frac = params.g(phase, P_SEND_FRACTION);
    let send = (avail * send_frac * 0.5) as i64;
    if send <= 0 { return None; }

    Some(vec![TAction::Send { source: strongest.id, target: weakest.id, count: send }])
}

fn handle_upgrade(
    state: &TState,
    cfg: &TConfig,
    my_suns: &[&TSun],
    total_available: f64,
    params: &EvolvedParams,
    phase: usize,
    player_id: i64,
) -> Option<Vec<TAction>> {
    let threshold = params.g(phase, P_UPGRADE_THRESHOLD);
    let max_level = params.gi(phase, P_MAX_UPGRADE_LEVEL);
    let upgrade_pref = params.g(phase, P_UPGRADE_VS_ATTACK);
    let eco_duration = params.g(phase, P_ECO_PHASE_DURATION);
    let no_target_pref = params.g(phase, P_UPGRADE_WHEN_NO_TARGETS);

    let eco_boost = if (state.tick as f64) < eco_duration { 0.3 } else { 0.0 };
    let has_targets = state.suns.values().any(|s| s.owner != player_id && s.owner != 0)
        || state.suns.values().any(|s| s.owner == 0);
    let no_target_boost = if !has_targets { no_target_pref } else { 0.0 };

    let effective_pref = upgrade_pref + eco_boost + no_target_boost;
    if effective_pref < 0.4 {
        return None;
    }

    let mut suns_sorted: Vec<&&TSun> = my_suns.iter().collect();
    suns_sorted.sort_by(|a, b| b.garrison.partial_cmp(&a.garrison).unwrap());

    for sun in suns_sorted {
        let effective_max = max_level.min(cfg.max_sun_level);
        if sun.level >= effective_max { continue; }
        let cost_idx = (sun.level - 1) as usize;
        if cost_idx >= cfg.upgrade_costs.len() { continue; }
        let cost = cfg.upgrade_costs[cost_idx];
        if sun.garrison >= threshold.max(cost as f64) {
            return Some(vec![TAction::Upgrade { sun_id: sun.id }]);
        }
    }

    None
}

fn handle_attack(
    state: &TState,
    cfg: &TConfig,
    my_suns: &[&TSun],
    available: &mut HashMap<i64, f64>,
    total_available: f64,
    params: &EvolvedParams,
    phase: usize,
    player_id: i64,
) -> Vec<TAction> {
    let targets: Vec<&TSun> = state.suns.values().filter(|s| s.owner != player_id).collect();
    if targets.is_empty() { return vec![]; }

    // Friendly incoming
    let my_ids: HashSet<i64> = my_suns.iter().map(|s| s.id).collect();
    let mut friendly_incoming: HashMap<i64, i64> = HashMap::new();
    for g in &state.groups {
        if my_ids.contains(&g.owner) {
            *friendly_incoming.entry(g.target_sun_id).or_insert(0) += g.count;
        }
    }

    // Score targets
    let reserve = params.g(phase, P_RESERVE_PER_SUN);
    let w_garrison = params.g(phase, P_W_GARRISON);
    let w_distance = params.g(phase, P_W_DISTANCE);
    let w_level = params.g(phase, P_W_LEVEL);
    let w_neutral = params.g(phase, P_W_NEUTRAL_BONUS);
    let w_enemy = params.g(phase, P_W_ENEMY_BONUS);
    let w_friendly = params.g(phase, P_W_INCOMING_FRIENDLY);
    let overkill = params.g(phase, P_OVERKILL_AVERSION);
    let nsw = params.g(phase, P_NEAREST_SUN_WEIGHT).clamp(0.0, 1.0);

    let total_avail: f64 = my_suns.iter().map(|s| (s.garrison - reserve).max(0.0)).sum();

    let mut scored: Vec<(f64, &TSun)> = Vec::new();
    for t in &targets {
        let dists: Vec<f64> = my_suns.iter().map(|s| dist(s.x, s.y, t.x, t.y)).collect();
        if dists.is_empty() { continue; }
        let min_d = dists.iter().cloned().fold(f64::INFINITY, f64::min);
        let avg_d: f64 = dists.iter().sum::<f64>() / dists.len() as f64;
        let eff_dist = nsw * min_d + (1.0 - nsw) * avg_d;

        let mut score = w_garrison * t.garrison;
        score += w_distance * eff_dist * 0.01;
        score -= w_level * t.level as f64;
        if t.owner == 0 { score -= w_neutral; } else { score -= w_enemy; }

        let incoming = *friendly_incoming.get(&t.id).unwrap_or(&0) as f64;
        score += w_friendly * incoming;

        if total_avail > 0.0 && t.garrison > 0.0 {
            let excess = ((total_avail - t.garrison * 2.0) / total_avail).max(0.0);
            score += overkill * excess;
        }

        scored.push((score, t));
    }
    scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

    let max_targets = params.gi(phase, P_MAX_TARGETS_PER_TICK) as usize;
    let patience = params.g(phase, P_PATIENCE);
    let min_ratio = params.g(phase, P_MIN_FORCE_RATIO);
    let eco_duration = params.g(phase, P_ECO_PHASE_DURATION);
    let early_agg = params.g(phase, P_EARLY_AGGRESSION);

    let mut effective_ratio = min_ratio * patience;
    if (state.tick as f64) < eco_duration {
        effective_ratio *= 1.0 - early_agg * 0.5;
    }

    let send_frac = params.g(phase, P_SEND_FRACTION);
    let concentrate = params.g(phase, P_CONCENTRATE_VS_SPLIT);

    let mut actions = Vec::new();

    for &(_score, target) in scored.iter().take(max_targets) {
        let needed = (target.garrison * effective_ratio).max(1.0);
        let current_total: f64 = available.values().sum();
        if current_total < needed { continue; }

        if concentrate > 0.5 {
            // Send from nearest sun only.
            let nearest = my_suns.iter()
                .min_by(|a, b| dist(a.x, a.y, target.x, target.y)
                    .partial_cmp(&dist(b.x, b.y, target.x, target.y)).unwrap())
                .unwrap();
            let avail = available.get(&nearest.id).copied().unwrap_or(0.0);
            let count = (avail * send_frac) as i64;
            if count > 0 {
                actions.push(TAction::Send { source: nearest.id, target: target.id, count });
                *available.get_mut(&nearest.id).unwrap() -= count as f64;
            }
        } else {
            for sun in my_suns {
                let avail = available.get(&sun.id).copied().unwrap_or(0.0);
                let count = (avail * send_frac) as i64;
                if count > 0 {
                    actions.push(TAction::Send { source: sun.id, target: target.id, count });
                    *available.get_mut(&sun.id).unwrap() -= count as f64;
                }
            }
        }
    }

    actions
}

// ── Public API ───────────────────────────────────────────────────────

/// Result of a training game, returned to Python.
#[pyclass(frozen)]
pub struct TrainingResult {
    #[pyo3(get)]
    pub winner: i64,
    #[pyo3(get)]
    pub ticks: i64,
    #[pyo3(get)]
    pub is_draw: bool,
}

/// Run a complete training game in pure Rust.
///
/// Both players use the evolved bot heuristic with their respective genomes.
/// Returns (winner_player_id, ticks, is_draw).
#[pyfunction]
pub fn run_training_game(
    // Game config
    config_py: &config::GameConfig,
    // Initial state as parallel arrays (avoids Python dict overhead)
    sun_ids: Vec<i64>,
    sun_xs: Vec<f64>,
    sun_ys: Vec<f64>,
    sun_owners: Vec<i64>,
    sun_garrisons: Vec<f64>,
    sun_levels: Vec<i64>,
    players: Vec<i64>,
    // Bot genomes
    genome_p1: Vec<f64>,
    genome_p2: Vec<f64>,
) -> TrainingResult {
    let cfg = TConfig {
        production_interval: config_py.production_interval,
        production_per_level: config_py.production_per_level,
        max_sun_level: config_py.max_sun_level,
        upgrade_costs: config_py.upgrade_costs.clone(),
        capture_level_reset: config_py.capture_level_reset,
        unit_speed: config_py.unit_speed,
        attack_ratio: config_py.attack_ratio,
        decision_interval: config_py.decision_interval,
        max_ticks: config_py.max_ticks,
    };

    let mut suns = HashMap::new();
    for i in 0..sun_ids.len() {
        suns.insert(sun_ids[i], TSun {
            id: sun_ids[i],
            x: sun_xs[i],
            y: sun_ys[i],
            owner: sun_owners[i],
            level: sun_levels[i],
            garrison: sun_garrisons[i],
            production_ticks: 0,
        });
    }

    let mut state = TState {
        suns,
        groups: Vec::new(),
        players: players.clone(),
        tick: 0,
        winner: None,
        eliminated: HashSet::new(),
    };

    let params_p1 = EvolvedParams::from_genome(&genome_p1);
    let params_p2 = EvolvedParams::from_genome(&genome_p2);
    let p1 = players[0];
    let p2 = players[1];

    while state.winner.is_none() {
        // Bot decisions
        if state.tick % cfg.decision_interval == 0 {
            if !state.eliminated.contains(&p1) {
                let actions = evolved_decide(&state, &cfg, &params_p1, p1);
                process_actions(&mut state, &cfg, p1, &actions);
            }
            if !state.eliminated.contains(&p2) {
                let actions = evolved_decide(&state, &cfg, &params_p2, p2);
                process_actions(&mut state, &cfg, p2, &actions);
            }
        }

        move_groups(&mut state);
        resolve_arrivals(&mut state, &cfg);
        produce_units(&mut state, &cfg);
        check_win(&mut state, &cfg);
        state.tick += 1;
    }

    let winner = state.winner.unwrap_or(0);
    TrainingResult {
        winner,
        ticks: state.tick,
        is_draw: winner == 0,
    }
}

// Re-use config module reference
use crate::config;
