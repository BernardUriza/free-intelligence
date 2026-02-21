// Setup state persistence — path, load, and save.

use std::path::PathBuf;

use super::SetupState;

/// Resolve the path to the setup state JSON file.
fn state_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("setup.json")
}

/// Load the setup state from disk (returns default if missing or corrupt).
pub(super) fn load() -> SetupState {
    let path = state_path();
    if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        SetupState::default()
    }
}

/// Persist the setup state to disk.
pub(super) fn save(state: &SetupState) -> Result<(), String> {
    let path = state_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Setup state saved to {:?}", path);
    Ok(())
}
