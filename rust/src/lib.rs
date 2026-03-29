use pyo3::prelude::*;

mod config;
mod state;
mod types;

/// The Clauralux game engine, implemented in Rust for performance.
#[pymodule]
fn _engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Types
    m.add_class::<types::Position>()?;

    // Config
    m.add_class::<config::GameConfig>()?;

    // State
    m.add_class::<state::Sun>()?;
    m.add_class::<state::UnitGroup>()?;
    m.add_class::<state::GameState>()?;

    Ok(())
}
