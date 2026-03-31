use pyo3::prelude::*;
use pyo3::types::PyDict;

/// All tunable game parameters. Immutable after creation.
#[pyclass(frozen, from_py_object)]
#[derive(Clone)]
pub struct GameConfig {
    #[pyo3(get)]
    pub map_width: f64,
    #[pyo3(get)]
    pub map_height: f64,
    #[pyo3(get)]
    pub production_interval: i64,
    #[pyo3(get)]
    pub production_per_level: i64,
    #[pyo3(get)]
    pub max_sun_level: i64,
    #[pyo3(get)]
    pub upgrade_costs: Vec<i64>,
    #[pyo3(get)]
    pub capture_level_reset: Option<i64>,
    #[pyo3(get)]
    pub unit_speed: f64,
    #[pyo3(get)]
    pub attack_ratio: f64,
    #[pyo3(get)]
    pub decision_interval: i64,
    #[pyo3(get)]
    pub max_ticks: Option<i64>,
    #[pyo3(get)]
    pub ticks_per_second: i64,
    #[pyo3(get)]
    pub default_neutral_garrison: f64,
    #[pyo3(get)]
    pub default_player_garrison: f64,
    #[pyo3(get)]
    pub seed: Option<i64>,
}

#[pymethods]
impl GameConfig {
    #[new]
    #[pyo3(signature = (
        map_width = 1000.0,
        map_height = 800.0,
        production_interval = 30,
        production_per_level = 1,
        max_sun_level = 3,
        upgrade_costs = None,
        capture_level_reset = Some(1),
        unit_speed = 2.0,
        attack_ratio = 1.0,
        decision_interval = 1,
        max_ticks = Some(30_000),
        ticks_per_second = 50,
        default_neutral_garrison = 10.0,
        default_player_garrison = 5.0,
        seed = Some(42),
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        map_width: f64,
        map_height: f64,
        production_interval: i64,
        production_per_level: i64,
        max_sun_level: i64,
        upgrade_costs: Option<Vec<i64>>,
        capture_level_reset: Option<i64>,
        unit_speed: f64,
        attack_ratio: f64,
        decision_interval: i64,
        max_ticks: Option<i64>,
        ticks_per_second: i64,
        default_neutral_garrison: f64,
        default_player_garrison: f64,
        seed: Option<i64>,
    ) -> PyResult<Self> {
        // Treat max_ticks <= 0 as None (no tick limit).
        let max_ticks = max_ticks.filter(|&t| t > 0);

        let upgrade_costs = upgrade_costs.unwrap_or_else(|| vec![20, 40]);

        // Validate: upgrade_costs must have enough entries for max_sun_level.
        // Need (max_sun_level - 1) costs (one per upgrade from level 1 to max).
        let needed = (max_sun_level - 1) as usize;
        if upgrade_costs.len() < needed {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "max_sun_level={} requires {} upgrade costs, but only {} provided",
                max_sun_level,
                needed,
                upgrade_costs.len()
            )));
        }

        Ok(GameConfig {
            map_width,
            map_height,
            production_interval,
            production_per_level,
            max_sun_level,
            upgrade_costs,
            capture_level_reset,
            unit_speed,
            attack_ratio,
            decision_interval,
            max_ticks,
            ticks_per_second,
            default_neutral_garrison,
            default_player_garrison,
            seed,
        })
    }

    /// Create a new GameConfig with specified fields overridden.
    /// Replaces dataclasses.replace() for Rust-backed types.
    #[pyo3(signature = (**kwargs))]
    fn replace(&self, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut new = self.clone();
        if let Some(kw) = kwargs {
            for (key, value) in kw.iter() {
                let key_str: String = key.extract()?;
                match key_str.as_str() {
                    "map_width" => new.map_width = value.extract()?,
                    "map_height" => new.map_height = value.extract()?,
                    "production_interval" => new.production_interval = value.extract()?,
                    "production_per_level" => new.production_per_level = value.extract()?,
                    "max_sun_level" => new.max_sun_level = value.extract()?,
                    "upgrade_costs" => new.upgrade_costs = value.extract()?,
                    "capture_level_reset" => new.capture_level_reset = value.extract()?,
                    "unit_speed" => new.unit_speed = value.extract()?,
                    "attack_ratio" => new.attack_ratio = value.extract()?,
                    "decision_interval" => new.decision_interval = value.extract()?,
                    "max_ticks" => {
                        let raw: Option<i64> = value.extract()?;
                        new.max_ticks = raw.filter(|&t| t > 0);
                    }
                    "ticks_per_second" => new.ticks_per_second = value.extract()?,
                    "default_neutral_garrison" => new.default_neutral_garrison = value.extract()?,
                    "default_player_garrison" => new.default_player_garrison = value.extract()?,
                    "seed" => new.seed = value.extract()?,
                    _ => {
                        return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                            "GameConfig has no field '{key_str}'"
                        )))
                    }
                }
            }
        }
        Ok(new)
    }

    fn __repr__(&self) -> String {
        format!(
            "GameConfig(map_width={}, map_height={}, production_interval={}, ...)",
            self.map_width, self.map_height, self.production_interval
        )
    }
}
