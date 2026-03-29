use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::{HashMap, HashSet};

use crate::types::Position;

/// A sun on the map. Produces units for its owner.
#[pyclass]
#[derive(Clone)]
pub struct Sun {
    #[pyo3(get, set)]
    pub id: i64,
    #[pyo3(get, set)]
    pub position: Position,
    #[pyo3(get, set)]
    pub owner: i64,
    #[pyo3(get, set)]
    pub level: i64,
    #[pyo3(get, set)]
    pub garrison: f64,
    #[pyo3(get, set)]
    pub production_ticks: i64,
}

#[pymethods]
impl Sun {
    #[new]
    #[pyo3(signature = (id, position, owner = 0, level = 1, garrison = 0.0, production_ticks = 0))]
    fn new(
        id: i64,
        position: Position,
        owner: i64,
        level: i64,
        garrison: f64,
        production_ticks: i64,
    ) -> Self {
        Sun {
            id,
            position,
            owner,
            level,
            garrison,
            production_ticks,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Sun(id={}, owner={}, level={}, garrison={:.1})",
            self.id, self.owner, self.level, self.garrison
        )
    }
}

/// A group of units travelling toward a target sun.
#[pyclass]
#[derive(Clone)]
pub struct UnitGroup {
    #[pyo3(get, set)]
    pub owner: i64,
    #[pyo3(get, set)]
    pub count: i64,
    #[pyo3(get, set)]
    pub position: Position,
    #[pyo3(get, set)]
    pub target_sun_id: i64,
    #[pyo3(get, set)]
    pub velocity_x: f64,
    #[pyo3(get, set)]
    pub velocity_y: f64,
}

#[pymethods]
impl UnitGroup {
    #[new]
    #[pyo3(signature = (owner, count, position, target_sun_id, velocity_x = 0.0, velocity_y = 0.0))]
    fn new(
        owner: i64,
        count: i64,
        position: Position,
        target_sun_id: i64,
        velocity_x: f64,
        velocity_y: f64,
    ) -> Self {
        UnitGroup {
            owner,
            count,
            position,
            target_sun_id,
            velocity_x,
            velocity_y,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "UnitGroup(owner={}, count={}, target={})",
            self.owner, self.count, self.target_sun_id
        )
    }
}

/// The complete mutable state of a game.
#[pyclass]
pub struct GameState {
    // Internal storage — Sun and UnitGroup are stored as Py<T> so Python
    // code can hold references and mutate them, and Rust tick() can also
    // access them via borrow/borrow_mut.
    pub(crate) suns_map: HashMap<i64, Py<Sun>>,
    pub(crate) groups: Vec<Py<UnitGroup>>,
    pub(crate) players_vec: Vec<i64>,
    pub(crate) tick_val: i64,
    pub(crate) winner_val: Option<i64>,
    pub(crate) eliminated_set: HashSet<i64>,
}

#[pymethods]
impl GameState {
    #[new]
    #[pyo3(signature = (suns = None, unit_groups = None, players = None, tick = 0, winner = None, eliminated = None))]
    fn new(
        py: Python<'_>,
        suns: Option<&Bound<'_, PyDict>>,
        unit_groups: Option<&Bound<'_, PyList>>,
        players: Option<Vec<i64>>,
        tick: i64,
        winner: Option<i64>,
        eliminated: Option<HashSet<i64>>,
    ) -> PyResult<Self> {
        let mut suns_map = HashMap::new();
        if let Some(d) = suns {
            for (key, value) in d.iter() {
                let id: i64 = key.extract()?;
                let sun: Py<Sun> = value.extract()?;
                suns_map.insert(id, sun);
            }
        }

        let mut groups = Vec::new();
        if let Some(l) = unit_groups {
            for item in l.iter() {
                let group: Py<UnitGroup> = item.extract()?;
                groups.push(group);
            }
        }

        Ok(GameState {
            suns_map,
            groups,
            players_vec: players.unwrap_or_default(),
            tick_val: tick,
            winner_val: winner,
            eliminated_set: eliminated.unwrap_or_default(),
        })
    }

    /// Returns suns as a Python dict[int, Sun].
    /// The returned Sun objects are the *same* objects stored internally,
    /// so mutations to them are visible to the game engine.
    /// Keys are sorted to match Python's insertion-ordered dict behavior.
    #[getter]
    fn suns(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);
        let mut keys: Vec<i64> = self.suns_map.keys().copied().collect();
        keys.sort();
        for id in keys {
            if let Some(sun) = self.suns_map.get(&id) {
                dict.set_item(id, sun.clone_ref(py))?;
            }
        }
        Ok(dict.into_any().unbind())
    }

    /// Returns unit_groups as a Python list[UnitGroup].
    #[getter]
    fn unit_groups(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let list = PyList::empty(py);
        for group in &self.groups {
            list.append(group.clone_ref(py))?;
        }
        Ok(list.into_any().unbind())
    }

    #[setter]
    fn set_unit_groups(&mut self, val: Vec<Py<UnitGroup>>) {
        self.groups = val;
    }

    #[getter]
    fn players(&self) -> Vec<i64> {
        self.players_vec.clone()
    }

    #[getter]
    fn tick(&self) -> i64 {
        self.tick_val
    }

    #[setter]
    fn set_tick(&mut self, val: i64) {
        self.tick_val = val;
    }

    #[getter]
    fn winner(&self) -> Option<i64> {
        self.winner_val
    }

    #[setter]
    fn set_winner(&mut self, val: Option<i64>) {
        self.winner_val = val;
    }

    #[getter]
    fn eliminated(&self) -> HashSet<i64> {
        self.eliminated_set.clone()
    }

    #[setter]
    fn set_eliminated(&mut self, val: HashSet<i64>) {
        self.eliminated_set = val;
    }

    /// Add a unit group to the internal list.
    fn add_unit_group(&mut self, group: Py<UnitGroup>) {
        self.groups.push(group);
    }

    /// Add/update a sun in the internal map.
    fn set_sun(&mut self, id: i64, sun: Py<Sun>) {
        self.suns_map.insert(id, sun);
    }

    /// Mark a player as eliminated.
    fn add_eliminated(&mut self, player_id: i64) {
        self.eliminated_set.insert(player_id);
    }

    /// Get a sun by ID (returns None if not found).
    fn get_sun(&self, py: Python<'_>, id: i64) -> Option<Py<Sun>> {
        self.suns_map.get(&id).map(|s| s.clone_ref(py))
    }

    fn __repr__(&self) -> String {
        format!(
            "GameState(tick={}, suns={}, groups={}, players={})",
            self.tick_val,
            self.suns_map.len(),
            self.groups.len(),
            self.players_vec.len(),
        )
    }
}
