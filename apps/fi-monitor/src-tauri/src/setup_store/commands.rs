// Tauri commands for setup wizard state.

use super::persistence;
use super::SetupState;

/// Save state and return it (DRY helper for mark_* commands).
fn save_and_return(state: SetupState) -> Result<SetupState, String> {
    persistence::save(&state)?;
    Ok(state)
}

/// Load setup state.
#[tauri::command]
pub(crate) fn get_setup_state() -> SetupState {
    persistence::load()
}

/// Update setup state.
#[tauri::command]
pub(crate) fn update_setup_state(state: SetupState) -> Result<SetupState, String> {
    save_and_return(state)
}

/// Mark setup as completed.
#[tauri::command]
pub(crate) fn mark_setup_completed(
    ollama_installed: bool,
    python_installed: bool,
) -> Result<SetupState, String> {
    save_and_return(SetupState {
        completed: true,
        ollama_installed,
        python_installed,
        last_check: Some(chrono::Utc::now().to_rfc3339()),
        skipped: false,
    })
}

/// Mark setup as skipped.
#[tauri::command]
pub(crate) fn mark_setup_skipped() -> Result<SetupState, String> {
    save_and_return(SetupState {
        completed: true,
        ollama_installed: false,
        python_installed: false,
        last_check: Some(chrono::Utc::now().to_rfc3339()),
        skipped: true,
    })
}
