use pyo3::prelude::*;

/// A 2D point on the game map.
#[pyclass(frozen, eq, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub struct Position {
    #[pyo3(get)]
    pub x: f64,
    #[pyo3(get)]
    pub y: f64,
}

// Pure Rust methods — callable from other Rust modules.
impl Position {
    pub fn distance_to(&self, other: &Position) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }

    pub fn direction_to(&self, other: &Position) -> (f64, f64) {
        let dist = self.distance_to(other);
        if dist == 0.0 {
            (0.0, 0.0)
        } else {
            ((other.x - self.x) / dist, (other.y - self.y) / dist)
        }
    }
}

#[pymethods]
impl Position {
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Position { x, y }
    }

    #[pyo3(name = "distance_to")]
    fn py_distance_to(&self, other: &Position) -> f64 {
        self.distance_to(other)
    }

    #[pyo3(name = "direction_to")]
    fn py_direction_to(&self, other: &Position) -> (f64, f64) {
        self.direction_to(other)
    }

    fn __repr__(&self) -> String {
        format!("Position(x={}, y={})", self.x, self.y)
    }
}
