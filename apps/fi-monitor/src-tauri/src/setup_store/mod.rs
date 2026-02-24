// Setup wizard state persistence.
//
// Persisted to: %APPDATA%\io.aurity.fi-monitor\setup.json

mod commands;
mod persistence;

pub(crate) use commands::{
    get_setup_state, mark_setup_completed, mark_setup_skipped, update_setup_state,
};

use serde::{Deserialize, Serialize};

/// Wizard completion state persisted to disk.
#[derive(Serialize, Deserialize, Clone, Default, Debug)]
pub struct SetupState {
    pub completed: bool,
    pub ollama_installed: bool,
    pub python_installed: bool,
    pub last_check: Option<String>,
    pub skipped: bool,
}
