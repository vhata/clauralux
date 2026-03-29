use pyo3::prelude::*;

mod config;
mod types;

/// The Clauralux game engine, implemented in Rust for performance.
#[pymodule]
fn _engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Types
    m.add_class::<types::Position>()?;

    // Config
    m.add_class::<config::GameConfig>()?;

    Ok(())
}
