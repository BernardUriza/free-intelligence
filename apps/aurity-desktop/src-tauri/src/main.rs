// Aurity Desktop - Main Entry Point
//
// This application manages:
// 1. FastAPI backend as a sidecar process
// 2. Tauri webview for the frontend
// 3. System tray integration
// 4. Health checks before showing UI

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

/// Backend server state
struct BackendState {
    is_ready: AtomicBool,
}

/// Check if the backend is healthy by calling /api/health
async fn check_backend_health() -> bool {
    let client = reqwest::Client::new();
    match client
        .get("http://localhost:7001/api/health")
        .timeout(Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Wait for backend to become healthy with retries
async fn wait_for_backend(max_retries: u32, delay_ms: u64) -> bool {
    for attempt in 1..=max_retries {
        if check_backend_health().await {
            println!("[Aurity] Backend healthy after {} attempts", attempt);
            return true;
        }
        println!(
            "[Aurity] Waiting for backend... attempt {}/{}",
            attempt, max_retries
        );
        tokio::time::sleep(Duration::from_millis(delay_ms)).await;
    }
    false
}

#[tauri::command]
async fn get_backend_status(state: tauri::State<'_, Arc<BackendState>>) -> Result<bool, String> {
    Ok(state.is_ready.load(Ordering::SeqCst))
}

#[tauri::command]
async fn check_ollama_status() -> Result<bool, String> {
    let client = reqwest::Client::new();
    match client
        .get("http://localhost:11434/api/tags")
        .timeout(Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

fn main() {
    let backend_state = Arc::new(BackendState {
        is_ready: AtomicBool::new(false),
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(backend_state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state = backend_state.clone();

            // Spawn backend sidecar
            println!("[Aurity] Starting backend sidecar...");

            let shell = app_handle.shell();
            let sidecar_command = shell
                .sidecar("aurity-backend")
                .expect("Failed to create sidecar command");

            // Spawn the sidecar process
            let (mut _rx, _child) = sidecar_command
                .spawn()
                .expect("Failed to spawn backend sidecar");

            // Wait for backend to be ready in a separate task
            let handle = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                println!("[Aurity] Waiting for backend to start...");

                // Wait up to 30 seconds for backend (30 retries * 1000ms)
                if wait_for_backend(30, 1000).await {
                    state.is_ready.store(true, Ordering::SeqCst);
                    println!("[Aurity] Backend is ready!");

                    // Emit event to frontend
                    let _ = handle.emit("backend-ready", true);
                } else {
                    eprintln!("[Aurity] ERROR: Backend failed to start within 30 seconds");
                    let _ = handle.emit("backend-error", "Backend failed to start");
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            check_ollama_status
        ])
        .run(tauri::generate_context!())
        .expect("Error while running Aurity Desktop");
}
