use pyo3::prelude::*;
use pyo3::types::PyTuple;

use crate::config::GameConfig;
use crate::state::GameState;
use crate::types::Position;

/// Immutable view of a sun, as seen by a bot.
#[pyclass(frozen)]
#[derive(Clone)]
pub struct SunView {
    #[pyo3(get)]
    pub id: i64,
    #[pyo3(get)]
    pub position: Position,
    #[pyo3(get)]
    pub owner: i64,
    #[pyo3(get)]
    pub level: i64,
    #[pyo3(get)]
    pub garrison: i64, // floored from internal float
}

#[pymethods]
impl SunView {
    #[new]
    fn new(id: i64, position: Position, owner: i64, level: i64, garrison: i64) -> Self {
        SunView {
            id,
            position,
            owner,
            level,
            garrison,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "SunView(id={}, owner={}, level={}, garrison={})",
            self.id, self.owner, self.level, self.garrison
        )
    }
}

/// Immutable view of a unit group in transit.
#[pyclass(frozen)]
#[derive(Clone)]
pub struct UnitGroupView {
    #[pyo3(get)]
    pub owner: i64,
    #[pyo3(get)]
    pub count: i64,
    #[pyo3(get)]
    pub position: Position,
    #[pyo3(get)]
    pub target_sun_id: i64,
}

#[pymethods]
impl UnitGroupView {
    #[new]
    fn new(owner: i64, count: i64, position: Position, target_sun_id: i64) -> Self {
        UnitGroupView {
            owner,
            count,
            position,
            target_sun_id,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "UnitGroupView(owner={}, count={}, target={})",
            self.owner, self.count, self.target_sun_id
        )
    }
}

/// Immutable snapshot of the game, provided to bots each decision tick.
#[pyclass(frozen)]
pub struct GameView {
    #[pyo3(get)]
    pub my_id: i64,
    #[pyo3(get)]
    pub tick: i64,
    pub(crate) suns_vec: Vec<Py<SunView>>,
    pub(crate) groups_vec: Vec<Py<UnitGroupView>>,
    #[pyo3(get)]
    pub config: Py<GameConfig>,
    pub(crate) players_vec: Vec<i64>,
    pub(crate) eliminated_set: Vec<i64>,
}

#[pymethods]
impl GameView {
    #[getter]
    fn suns<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, &self.suns_vec)
    }

    #[getter]
    fn unit_groups<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, &self.groups_vec)
    }

    #[getter]
    fn players<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, &self.players_vec)
    }

    #[getter]
    fn eliminated<'py>(&self, py: Python<'py>) -> PyResult<Py<PyAny>> {
        let set = pyo3::types::PyFrozenSet::new(py, &self.eliminated_set)?;
        Ok(set.into_any().unbind())
    }

    fn my_suns<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let my_id = self.my_id;
        let filtered: Vec<_> = self
            .suns_vec
            .iter()
            .filter(|s| s.get().owner == my_id)
            .collect();
        PyTuple::new(py, &filtered)
    }

    fn enemy_suns<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let my_id = self.my_id;
        let filtered: Vec<_> = self
            .suns_vec
            .iter()
            .filter(|s| {
                let owner = s.get().owner;
                owner != my_id && owner != 0 // 0 = NEUTRAL
            })
            .collect();
        PyTuple::new(py, &filtered)
    }

    fn neutral_suns<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let filtered: Vec<_> = self
            .suns_vec
            .iter()
            .filter(|s| s.get().owner == 0) // 0 = NEUTRAL
            .collect();
        PyTuple::new(py, &filtered)
    }

    fn sun_by_id(&self, py: Python<'_>, sun_id: i64) -> Option<Py<SunView>> {
        self.suns_vec
            .iter()
            .find(|s| s.get().id == sun_id)
            .map(|s| s.clone_ref(py))
    }

    fn my_unit_groups<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let my_id = self.my_id;
        let filtered: Vec<_> = self
            .groups_vec
            .iter()
            .filter(|g| g.get().owner == my_id)
            .collect();
        PyTuple::new(py, &filtered)
    }

    fn enemy_unit_groups<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let my_id = self.my_id;
        let filtered: Vec<_> = self
            .groups_vec
            .iter()
            .filter(|g| {
                let owner = g.get().owner;
                owner != my_id && owner != 0
            })
            .collect();
        PyTuple::new(py, &filtered)
    }

    /// Build a GameView snapshot from the mutable GameState.
    #[staticmethod]
    #[pyo3(name = "from_state")]
    fn py_from_state(
        py: Python<'_>,
        state: &GameState,
        player_id: i64,
        config: Py<GameConfig>,
    ) -> PyResult<Self> {
        Self::from_state(py, state, player_id, config)
    }
}

// Pure Rust method — callable from game.rs.
impl GameView {
    pub fn from_state(
        py: Python<'_>,
        state: &GameState,
        player_id: i64,
        config: Py<GameConfig>,
    ) -> PyResult<Self> {
        let mut suns_vec = Vec::new();
        let mut keys: Vec<i64> = state.suns_map.keys().copied().collect();
        keys.sort();
        for id in keys {
            if let Some(sun_py) = state.suns_map.get(&id) {
                let sun = sun_py.borrow(py);
                let sv = Py::new(
                    py,
                    SunView {
                        id: sun.id,
                        position: sun.position,
                        owner: sun.owner,
                        level: sun.level,
                        garrison: sun.garrison as i64, // floor
                    },
                )?;
                suns_vec.push(sv);
            }
        }

        let mut groups_vec = Vec::new();
        for group_py in &state.groups {
            let group = group_py.borrow(py);
            let gv = Py::new(
                py,
                UnitGroupView {
                    owner: group.owner,
                    count: group.count,
                    position: group.position,
                    target_sun_id: group.target_sun_id,
                },
            )?;
            groups_vec.push(gv);
        }

        Ok(GameView {
            my_id: player_id,
            tick: state.tick_val,
            suns_vec,
            groups_vec,
            config,
            players_vec: state.players_vec.clone(),
            eliminated_set: state.eliminated_set.iter().copied().collect(),
        })
    }
}
