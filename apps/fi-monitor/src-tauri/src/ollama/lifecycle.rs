// Lifecycle — start and stop the local Ollama process.

use std::process::{Command, Stdio};
use std::sync::Arc;
use std::time::Duration;

use tokio::time::sleep;

use super::health::check_ollama;
use crate::state::{kill_process, kill_process_by_name, AppState, OLLAMA_PORT};

/// Start Ollama if it isn't already running.
#[tauri::command]
pub(crate) async fn start_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_ollama().await {
        *state.ollama_running.lock().unwrap() = true;
        return Ok(true);
    }

    println!("[FI Monitor] Starting Ollama...");

    let result = Command::new("ollama")
        .arg("serve")
        .env("OLLAMA_ORIGINS", "*")
        .env("OLLAMA_HOST", format!("0.0.0.0:{}", OLLAMA_PORT))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();

    match result {
        Ok(child) => {
            let pid = child.id();
            *state.ollama_process.lock().unwrap() = Some(pid);

            // Poll until Ollama responds or we time out (15s)
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_ollama().await {
                    *state.ollama_running.lock().unwrap() = true;
                    println!("[FI Monitor] Ollama started (PID: {})", pid);
                    return Ok(true);
                }
            }

            Err("Ollama started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start Ollama: {}", e)),
    }
}

/// Stop the Ollama process.
#[tauri::command]
pub(crate) async fn stop_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Ollama...");

    if let Some(pid) = state.ollama_process.lock().unwrap().take() {
        // Kill our own process by PID (precise — won't touch user's other ollama instances)
        println!("[FI Monitor] Killing Ollama PID {}", pid);
        kill_process(pid);
    } else {
        // Fallback: ollama was running before FI Monitor started, kill by name
        #[cfg(target_os = "windows")]
        kill_process_by_name("ollama.exe");
        #[cfg(not(target_os = "windows"))]
        kill_process_by_name("ollama");
    }

    *state.ollama_running.lock().unwrap() = false;
    Ok(true)
}
