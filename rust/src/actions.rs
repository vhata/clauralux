use pyo3::prelude::*;

/// Send units from one sun to another.
#[pyclass(frozen)]
#[derive(Clone)]
pub struct SendUnits {
    #[pyo3(get)]
    pub source_sun_id: i64,
    #[pyo3(get)]
    pub target_sun_id: i64,
    #[pyo3(get)]
    pub count: i64,
}

#[pymethods]
impl SendUnits {
    #[new]
    fn new(source_sun_id: i64, target_sun_id: i64, count: i64) -> Self {
        SendUnits {
            source_sun_id,
            target_sun_id,
            count,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "SendUnits(source={}, target={}, count={})",
            self.source_sun_id, self.target_sun_id, self.count
        )
    }
}

/// Spend garrison units to upgrade a sun's level.
#[pyclass(frozen)]
#[derive(Clone)]
pub struct UpgradeSun {
    #[pyo3(get)]
    pub sun_id: i64,
}

#[pymethods]
impl UpgradeSun {
    #[new]
    fn new(sun_id: i64) -> Self {
        UpgradeSun { sun_id }
    }

    fn __repr__(&self) -> String {
        format!("UpgradeSun(sun_id={})", self.sun_id)
    }
}
