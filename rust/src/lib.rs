use pyo3::prelude::*;

mod actions;
mod bots;
mod config;
mod game;
mod state;
mod training;
mod types;
mod view;

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

    // Actions
    m.add_class::<actions::SendUnits>()?;
    m.add_class::<actions::UpgradeSun>()?;

    // Views
    m.add_class::<view::SunView>()?;
    m.add_class::<view::UnitGroupView>()?;
    m.add_class::<view::GameView>()?;

    // Game
    m.add_class::<game::Game>()?;

    // Training
    m.add_class::<training::TrainingResult>()?;
    m.add_function(wrap_pyfunction!(training::run_training_game, m)?)?;
    m.add_function(wrap_pyfunction!(training::run_neural_training_game, m)?)?;
    m.add_function(wrap_pyfunction!(training::run_training_game_vs_bot, m)?)?;

    Ok(())
}
