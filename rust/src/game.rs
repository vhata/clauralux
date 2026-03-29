use pyo3::prelude::*;

use crate::actions::{SendUnits, UpgradeSun};
use crate::config::GameConfig;
use crate::state::{GameState, Sun, UnitGroup};
use crate::types::Position;
use crate::view::GameView;

/// Internal action representation — avoids crossing the Python/Rust boundary
/// during tick processing.
enum ActionData {
    Send {
        source: i64,
        target: i64,
        count: i64,
    },
    Upgrade {
        sun_id: i64,
    },
}

/// The core game simulation. Tick-based, deterministic.
#[pyclass]
pub struct Game {
    config: Py<GameConfig>,
    state: Py<GameState>,
    pending: Vec<(i64, Vec<ActionData>)>, // (player_id, actions)
}

#[pymethods]
impl Game {
    #[new]
    fn new(config: Py<GameConfig>, state: Py<GameState>) -> Self {
        Game {
            config,
            state,
            pending: Vec::new(),
        }
    }

    #[getter]
    fn config(&self, py: Python<'_>) -> Py<GameConfig> {
        self.config.clone_ref(py)
    }

    #[getter]
    fn state(&self, py: Python<'_>) -> Py<GameState> {
        self.state.clone_ref(py)
    }

    #[getter]
    fn is_over(&self, py: Python<'_>) -> bool {
        self.state.borrow(py).winner_val.is_some()
    }

    fn get_view(&self, py: Python<'_>, player_id: i64) -> PyResult<GameView> {
        let state = self.state.borrow(py);
        GameView::from_state(py, &state, player_id, self.config.clone_ref(py))
    }

    fn apply_actions(
        &mut self,
        py: Python<'_>,
        player_id: i64,
        actions: Vec<Py<PyAny>>,
    ) -> PyResult<()> {
        if self.state.borrow(py).eliminated_set.contains(&player_id) {
            return Ok(());
        }

        let mut action_data = Vec::with_capacity(actions.len());
        for action in &actions {
            let obj = action.bind(py);
            if let Ok(send) = obj.downcast::<SendUnits>() {
                let s = send.get();
                action_data.push(ActionData::Send {
                    source: s.source_sun_id,
                    target: s.target_sun_id,
                    count: s.count,
                });
            } else if let Ok(upgrade) = obj.downcast::<UpgradeSun>() {
                let u = upgrade.get();
                action_data.push(ActionData::Upgrade { sun_id: u.sun_id });
            }
        }

        self.pending.retain(|(pid, _)| *pid != player_id);
        self.pending.push((player_id, action_data));
        Ok(())
    }

    fn tick(&mut self, py: Python<'_>) -> PyResult<()> {
        if self.state.borrow(py).winner_val.is_some() {
            return Ok(());
        }

        self.process_actions(py)?;
        self.move_unit_groups(py);
        self.resolve_arrivals(py)?;
        self.produce_units(py);
        self.check_win_condition(py);

        self.state.borrow_mut(py).tick_val += 1;
        Ok(())
    }
}

impl Game {
    fn process_actions(&mut self, py: Python<'_>) -> PyResult<()> {
        let pending = std::mem::take(&mut self.pending);
        for (player_id, actions) in &pending {
            for action in actions {
                match action {
                    ActionData::Send {
                        source,
                        target,
                        count,
                    } => {
                        self.process_send(py, *player_id, *source, *target, *count)?;
                    }
                    ActionData::Upgrade { sun_id } => {
                        self.process_upgrade(py, *player_id, *sun_id);
                    }
                }
            }
        }
        Ok(())
    }

    fn process_send(
        &self,
        py: Python<'_>,
        player_id: i64,
        source_id: i64,
        target_id: i64,
        count: i64,
    ) -> PyResult<()> {
        if source_id == target_id || count <= 0 {
            return Ok(());
        }

        // Get references to source and target suns.
        let st = self.state.borrow(py);
        let (sun_py, target_py) = match (st.suns_map.get(&source_id), st.suns_map.get(&target_id))
        {
            (Some(s), Some(t)) => (s.clone_ref(py), t.clone_ref(py)),
            _ => return Ok(()),
        };
        drop(st);

        // Validate and compute.
        let (sun_pos, target_pos, actual_count) = {
            let sun = sun_py.borrow(py);
            if sun.owner != player_id {
                return Ok(());
            }
            let actual = count.min(sun.garrison as i64);
            if actual <= 0 {
                return Ok(());
            }
            (sun.position, target_py.borrow(py).position, actual)
        };

        // Deduct garrison.
        sun_py.borrow_mut(py).garrison -= actual_count as f64;

        // Compute velocity.
        let (dx, dy) = sun_pos.direction_to(&target_pos);
        let speed = self.config.get().unit_speed;

        let group = Py::new(
            py,
            UnitGroup {
                owner: player_id,
                count: actual_count,
                position: Position {
                    x: sun_pos.x,
                    y: sun_pos.y,
                },
                target_sun_id: target_id,
                velocity_x: dx * speed,
                velocity_y: dy * speed,
            },
        )?;

        self.state.borrow_mut(py).groups.push(group);
        Ok(())
    }

    fn process_upgrade(&self, py: Python<'_>, player_id: i64, sun_id: i64) {
        let st = self.state.borrow(py);
        let Some(sun_py) = st.suns_map.get(&sun_id) else {
            return;
        };
        let sun_py = sun_py.clone_ref(py);
        drop(st);

        let cfg = self.config.get();
        let (owner, level, garrison) = {
            let sun = sun_py.borrow(py);
            (sun.owner, sun.level, sun.garrison)
        };

        if owner != player_id || level >= cfg.max_sun_level {
            return;
        }
        let cost_index = (level - 1) as usize;
        if cost_index >= cfg.upgrade_costs.len() {
            return;
        }
        let cost = cfg.upgrade_costs[cost_index];
        if (garrison as i64) < cost {
            return;
        }

        let mut sun = sun_py.borrow_mut(py);
        sun.garrison -= cost as f64;
        sun.level += 1;
    }

    fn move_unit_groups(&self, py: Python<'_>) {
        // Collect group refs first to avoid borrow conflicts.
        let st = self.state.borrow(py);
        let group_refs: Vec<Py<UnitGroup>> =
            st.groups.iter().map(|g| g.clone_ref(py)).collect();
        drop(st);

        for group_py in &group_refs {
            let mut group = group_py.borrow_mut(py);
            group.position = Position {
                x: group.position.x + group.velocity_x,
                y: group.position.y + group.velocity_y,
            };
        }
    }

    fn resolve_arrivals(&self, py: Python<'_>) -> PyResult<()> {
        let unit_speed = self.config.get().unit_speed;
        let attack_ratio = self.config.get().attack_ratio;
        let capture_level_reset = self.config.get().capture_level_reset;

        // Classify groups into arrived vs remaining.
        let st = self.state.borrow(py);
        let mut remaining: Vec<Py<UnitGroup>> = Vec::new();
        let mut arrived: Vec<(i64, i64, i64)> = Vec::new(); // (owner, count, target_id)

        for group_py in &st.groups {
            let group = group_py.borrow(py);
            let target_id = group.target_sun_id;
            if let Some(target_py) = st.suns_map.get(&target_id) {
                let target = target_py.borrow(py);
                let dist = group.position.distance_to(&target.position);
                drop(target);
                drop(group);
                if dist <= unit_speed {
                    let g = group_py.borrow(py);
                    arrived.push((g.owner, g.count, g.target_sun_id));
                } else {
                    remaining.push(group_py.clone_ref(py));
                }
            }
            // If target doesn't exist, group is discarded.
        }
        drop(st);

        // Replace groups with remaining.
        self.state.borrow_mut(py).groups = remaining;

        // Process arrivals.
        for (owner, count, target_id) in arrived {
            let st = self.state.borrow(py);
            let Some(target_py) = st.suns_map.get(&target_id) else {
                continue;
            };
            let target_py = target_py.clone_ref(py);
            drop(st);

            let target_owner = target_py.borrow(py).owner;
            if owner == target_owner {
                target_py.borrow_mut(py).garrison += count as f64;
            } else {
                let damage = count as f64 * attack_ratio;
                target_py.borrow_mut(py).garrison -= damage;
                if target_py.borrow(py).garrison <= 0.0 {
                    let remaining_units = target_py.borrow(py).garrison.abs() / attack_ratio;
                    let mut t = target_py.borrow_mut(py);
                    t.owner = owner;
                    t.garrison = remaining_units;
                    t.production_ticks = 0;
                    if let Some(reset) = capture_level_reset {
                        t.level = reset;
                    }
                }
            }
        }
        Ok(())
    }

    fn produce_units(&self, py: Python<'_>) {
        let cfg = self.config.get();
        let production_interval = cfg.production_interval;
        let production_per_level = cfg.production_per_level;

        // Collect sun refs to avoid holding state borrow during mutation.
        let st = self.state.borrow(py);
        let sun_refs: Vec<Py<Sun>> = st.suns_map.values().map(|s| s.clone_ref(py)).collect();
        drop(st);

        for sun_py in &sun_refs {
            let mut sun = sun_py.borrow_mut(py);
            if sun.owner == 0 {
                // NEUTRAL — skip.
                continue;
            }
            sun.production_ticks += 1;
            let prod_rate = (sun.level * production_per_level).max(1);
            let ticks_per_unit = production_interval / prod_rate;
            if ticks_per_unit > 0 && sun.production_ticks >= ticks_per_unit {
                sun.garrison += 1.0;
                sun.production_ticks = 0;
            }
        }
    }

    fn check_win_condition(&self, py: Python<'_>) {
        let mut st = self.state.borrow_mut(py);
        let players = st.players_vec.clone();

        for &player_id in &players {
            if st.eliminated_set.contains(&player_id) {
                continue;
            }
            let owns_suns = st
                .suns_map
                .values()
                .any(|s| s.borrow(py).owner == player_id);
            let has_groups = st.groups.iter().any(|g| g.borrow(py).owner == player_id);
            if !owns_suns && !has_groups {
                st.eliminated_set.insert(player_id);
            }
        }

        let active: Vec<i64> = players
            .iter()
            .filter(|p| !st.eliminated_set.contains(p))
            .copied()
            .collect();

        if active.len() == 1 {
            st.winner_val = Some(active[0]);
        } else if active.is_empty() {
            st.winner_val = Some(0); // NEUTRAL = draw
        } else if let Some(max_ticks) = self.config.get().max_ticks {
            if st.tick_val >= max_ticks {
                st.winner_val = Some(0); // draw by timeout
            }
        }
    }
}
