// Ollama — health checks and edge infrastructure management.

use std::path::PathBuf;

use log::info;

use crate::constants::{OLLAMA_API_URL, OLLAMA_CHECK_TIMEOUT};
use crate::errors::AppError;

/// Check if Ollama is responding to API requests.
/// Reusable helper to avoid repeating the same check in 3+ places.
pub(crate) async fn is_ollama_running() -> bool {
    let Ok(client) = reqwest::Client::builder()
        .timeout(OLLAMA_CHECK_TIMEOUT)
        .build()
    else {
        return false;
    };
    let url = format!("{}/api/tags", OLLAMA_API_URL);
    client
        .get(&url)
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

/// Check if Ollama is running locally
#[tauri::command]
pub async fn check_ollama_status() -> Result<bool, AppError> {
    Ok(is_ollama_running().await)
}

/// Ensure Ollama/Edge infrastructure is running
/// On Windows: runs ollama-tunnel.ps1 start
/// On macOS/Linux: runs ollama-tunnel.sh start
#[tauri::command]
pub async fn ensure_edge_infrastructure(_app: tauri::AppHandle) -> Result<String, AppError> {
    if is_ollama_running().await {
        return Ok("Ollama already running".to_string());
    }

    // Ollama not running - execute the tunnel script
    info!("Ollama not running, starting edge infrastructure...");

    // Find the scripts directory (relative to app or project root)
    let scripts_dir = find_scripts_dir();

    #[cfg(target_os = "windows")]
    {
        use std::process::Command;

        let script_path = scripts_dir.join("ollama-tunnel.ps1");
        if !script_path.exists() {
            return Err(AppError::Script(format!(
                "Script not found: {:?}",
                script_path
            )));
        }

        let output = Command::new("powershell")
            .args([
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                &script_path.to_string_lossy(),
                "start",
            ])
            .current_dir(&scripts_dir)
            .output()
            .map_err(|e| AppError::Script(format!("Failed to execute script: {}", e)))?;

        if output.status.success() {
            Ok("Edge infrastructure started (Windows)".to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(AppError::Script(format!("Script failed: {}", stderr)))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        use std::process::Command;

        let script_path = scripts_dir.join("ollama-tunnel.sh");
        if !script_path.exists() {
            return Err(AppError::Script(format!(
                "Script not found: {:?}",
                script_path
            )));
        }

        let output = Command::new("bash")
            .args([&script_path.to_string_lossy().to_string(), "start"])
            .current_dir(&scripts_dir)
            .output()
            .map_err(|e| AppError::Script(format!("Failed to execute script: {}", e)))?;

        if output.status.success() {
            Ok("Edge infrastructure started (Unix)".to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(AppError::Script(format!("Script failed: {}", stderr)))
        }
    }
}

/// Find the scripts directory by searching candidate paths.
fn find_scripts_dir() -> PathBuf {
    let candidates = vec![
        PathBuf::from("scripts"),
        PathBuf::from("../../../scripts"),
        PathBuf::from("../../scripts"),
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("scripts")))
            .unwrap_or_default(),
    ];

    for candidate in candidates {
        if candidate.exists() && candidate.is_dir() {
            return candidate;
        }
    }

    // Fallback
    PathBuf::from("scripts")
}
