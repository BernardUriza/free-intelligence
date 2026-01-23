// Setup State Persistence using Tauri Store
//
// Manages the setup wizard completion state. Persisted to:
// %APPDATA%\io.aurity.fi-monitor\setup.json

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Clone, Default, Debug)]
pub struct SetupState {
    pub completed: bool,
    pub ollama_installed: bool,
    pub python_installed: bool,
    pub last_check: Option<String>,
    pub skipped: bool,
}

fn get_setup_state_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("setup.json")
}

fn load_setup_state_internal() -> SetupState {
    let path = get_setup_state_path();
    if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        SetupState::default()
    }
}

fn save_setup_state_internal(state: &SetupState) -> Result<(), String> {
    let path = get_setup_state_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Setup state saved to {:?}", path);
    Ok(())
}

/// Load setup state
#[tauri::command]
pub fn get_setup_state() -> SetupState {
    load_setup_state_internal()
}

/// Update setup state
#[tauri::command]
pub fn update_setup_state(state: SetupState) -> Result<SetupState, String> {
    save_setup_state_internal(&state)?;
    Ok(state)
}

/// Mark setup as completed
#[tauri::command]
pub fn mark_setup_completed(
    ollama_installed: bool,
    python_installed: bool,
) -> Result<SetupState, String> {
    let state = SetupState {
        completed: true,
        ollama_installed,
        python_installed,
        last_check: Some(chrono::Utc::now().to_rfc3339()),
        skipped: false,
    };
    save_setup_state_internal(&state)?;
    Ok(state)
}

/// Mark setup as skipped
#[tauri::command]
pub fn mark_setup_skipped() -> Result<SetupState, String> {
    let state = SetupState {
        completed: true,
        ollama_installed: false,
        python_installed: false,
        last_check: Some(chrono::Utc::now().to_rfc3339()),
        skipped: true,
    };
    save_setup_state_internal(&state)?;
    Ok(state)
}
