// Wizard — first-run status, wizard state persistence, Python verification.

use std::fs;
use std::path::PathBuf;

use log::info;
use serde::{Deserialize, Serialize};

use crate::config::{atomic_write, get_data_dir};
use crate::errors::AppError;
use crate::ollama::is_ollama_running;

// =============================================================================
// TYPES
// =============================================================================

/// Wizard state persisted to filesystem (~/.aurity/config/wizard-state.json)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WizardState {
    pub version: u32,
    pub desktop_setup_completed: bool,
    pub desktop_setup_completed_at: Option<String>,
    pub fi_monitor_installed: Option<bool>,
}

/// First-run status for frontend wizard
#[derive(Serialize)]
pub struct FirstRunStatus {
    config_initialized: bool,
    ollama_available: bool,
    data_dir: String,
}

/// Python installation status
#[derive(Serialize)]
pub struct PythonStatus {
    installed: bool,
    version: Option<String>,
    pip_available: bool,
    fi_monitor_deps_installed: bool,
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/// Get the path to wizard state file
fn get_wizard_state_path(app: &tauri::AppHandle) -> Result<PathBuf, AppError> {
    let data_dir = get_data_dir(app)?;
    Ok(data_dir.join("config").join("wizard-state.json"))
}

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Get wizard state from filesystem
#[tauri::command]
pub fn get_wizard_state(app: tauri::AppHandle) -> Result<WizardState, AppError> {
    let state_path = get_wizard_state_path(&app)?;

    if !state_path.exists() {
        // File doesn't exist - return default state (wizard not completed)
        return Ok(WizardState::default());
    }

    // Verify it's a regular file, not a symlink (security check)
    if state_path.is_symlink() {
        return Err(AppError::Config(
            "Security: wizard state file is a symlink, refusing to read".into(),
        ));
    }

    let content = fs::read_to_string(&state_path)?;
    Ok(serde_json::from_str(&content)?)
}

/// Mark desktop setup as complete
#[tauri::command]
pub fn mark_desktop_setup_complete(
    app: tauri::AppHandle,
    fi_monitor_installed: bool,
) -> Result<WizardState, AppError> {
    let state_path = get_wizard_state_path(&app)?;

    // Ensure parent directory exists
    if let Some(parent) = state_path.parent() {
        fs::create_dir_all(parent)?;
    }

    // Create new state
    let state = WizardState {
        version: 1,
        desktop_setup_completed: true,
        desktop_setup_completed_at: Some(chrono::Utc::now().to_rfc3339()),
        fi_monitor_installed: Some(fi_monitor_installed),
    };

    // Serialize to JSON
    let content = serde_json::to_string_pretty(&state)?;

    // Write atomically
    atomic_write(&state_path, content.as_bytes())?;

    info!(
        "Wizard state saved: desktop_setup_completed=true, fi_monitor_installed={}",
        fi_monitor_installed
    );

    Ok(state)
}

/// Reset wizard state (for development/testing)
#[tauri::command]
pub fn reset_wizard_state(app: tauri::AppHandle) -> Result<bool, AppError> {
    let state_path = get_wizard_state_path(&app)?;

    if state_path.exists() {
        fs::remove_file(&state_path)?;
        info!("Wizard state reset (file deleted)");
        Ok(true)
    } else {
        info!("Wizard state reset (file didn't exist)");
        Ok(false)
    }
}

/// Check first-run status (for frontend wizard)
#[tauri::command]
pub async fn check_first_run_status(app: tauri::AppHandle) -> Result<FirstRunStatus, AppError> {
    let data_dir = get_data_dir(&app)?;
    let config_exists = data_dir.join("config/fi.policy.yaml").exists();

    // Check Ollama
    let ollama_ok = is_ollama_running().await;

    Ok(FirstRunStatus {
        config_initialized: config_exists,
        ollama_available: ollama_ok,
        data_dir: data_dir.to_string_lossy().to_string(),
    })
}

/// Check Python 3.14+ installation and dependencies
#[tauri::command]
pub async fn check_python_installation() -> Result<PythonStatus, AppError> {
    use std::process::Command;

    // Check python --version
    let version_output = Command::new("python").arg("--version").output();

    let (installed, version) = match version_output {
        Ok(output) if output.status.success() => {
            let v = String::from_utf8_lossy(&output.stdout).to_string();
            (true, Some(v.trim().to_string()))
        }
        _ => (false, None),
    };

    if !installed {
        return Ok(PythonStatus {
            installed: false,
            version: None,
            pip_available: false,
            fi_monitor_deps_installed: false,
        });
    }

    // Check pip
    let pip_output = Command::new("python")
        .args(["-m", "pip", "--version"])
        .output();
    let pip_available = pip_output.map(|o| o.status.success()).unwrap_or(false);

    // Check fi-monitor deps (fastapi, uvicorn, httpx, sentence_transformers)
    let deps_check = Command::new("python")
        .args([
            "-c",
            "import fastapi, uvicorn, httpx, sentence_transformers",
        ])
        .output();
    let fi_monitor_deps_installed = deps_check.map(|o| o.status.success()).unwrap_or(false);

    Ok(PythonStatus {
        installed,
        version,
        pip_available,
        fi_monitor_deps_installed,
    })
}
