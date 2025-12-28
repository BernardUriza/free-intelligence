// Aurity Desktop - Main Entry Point
//
// This application manages:
// 1. FastAPI backend as a sidecar process with DYNAMIC port allocation
// 2. Tauri webview for the frontend
// 3. Splashscreen while loading
// 4. Health checks before showing UI
// 5. Proper lifecycle management (cleanup on exit)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpListener;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tokio::time::sleep;

/// Global state for backend
struct BackendState {
    port: AtomicU16,
    is_ready: AtomicBool,
}

/// Find an available port based on build mode
/// Port allocation:
///   - 7001-7050: Cloud (reserved)
///   - 7051: Desktop dev (fixed, debug builds)
///   - 7052+: Desktop production (dynamic, release builds)
fn find_available_port() -> Option<u16> {
    // In debug mode, use fixed port 7051 for desktop dev
    #[cfg(debug_assertions)]
    {
        let port = 7051;
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Some(port);
        }
        // Fallback to dynamic if 7051 is busy
        for p in 7052..8000 {
            if TcpListener::bind(("127.0.0.1", p)).is_ok() {
                return Some(p);
            }
        }
        None
    }

    // In release mode, use dynamic port starting at 7052
    #[cfg(not(debug_assertions))]
    {
        for port in 7052..8000 {
            if TcpListener::bind(("127.0.0.1", port)).is_ok() {
                return Some(port);
            }
        }
        None
    }
}

/// Check if the backend is responding to health checks
async fn check_backend_health(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{}/api/health", port);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();

    match client.get(&url).send().await {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Emit loading status to splashscreen
fn emit_status(app: &tauri::AppHandle, message: &str) {
    let _ = app.emit("loading-status", message);
}

/// Get the backend URL (with dynamic port)
#[tauri::command]
fn get_backend_url(state: tauri::State<'_, Arc<BackendState>>) -> String {
    let port = state.port.load(Ordering::SeqCst);
    format!("http://127.0.0.1:{}", port)
}

/// Check if backend is ready
#[tauri::command]
fn get_backend_status(state: tauri::State<'_, Arc<BackendState>>) -> bool {
    state.is_ready.load(Ordering::SeqCst)
}

/// Check if Ollama is running locally
#[tauri::command]
async fn check_ollama_status() -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    match client.get("http://localhost:11434/api/tags").send().await {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

fn main() {
    let backend_state = Arc::new(BackendState {
        port: AtomicU16::new(0),
        is_ready: AtomicBool::new(false),
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(backend_state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state = backend_state.clone();

            // Spawn async task to start backend
            tauri::async_runtime::spawn(async move {
                // Step 1: Find available port
                emit_status(&app_handle, "Buscando puerto disponible...");

                let port = match find_available_port() {
                    Some(p) => {
                        println!("[Aurity] Selected port {} for backend", p);
                        p
                    }
                    None => {
                        eprintln!("[Aurity] ERROR: No available ports in range 7001-7999");
                        emit_status(&app_handle, "Error: No hay puertos disponibles");
                        return;
                    }
                };

                state.port.store(port, Ordering::SeqCst);

                // Step 2: Start the sidecar with the selected port
                emit_status(&app_handle, "Iniciando backend de IA...");

                let shell = app_handle.shell();
                let sidecar_result = shell
                    .sidecar("aurity-backend")
                    .expect("Failed to create sidecar command")
                    .args(["--port", &port.to_string()])
                    .spawn();

                match sidecar_result {
                    Ok((mut rx, _child)) => {
                        println!("[Aurity] Backend sidecar started");

                        // The tauri-plugin-process automatically handles cleanup on app exit

                        // Log sidecar output in background
                        let status_handle = app_handle.clone();
                        tauri::async_runtime::spawn(async move {
                            while let Some(event) = rx.recv().await {
                                match event {
                                    tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                                        let line_str = String::from_utf8_lossy(&line);
                                        println!("[backend] {}", line_str);

                                        // Detect when uvicorn is ready
                                        if line_str.contains("Uvicorn running")
                                            || line_str.contains("Application startup complete")
                                        {
                                            emit_status(&status_handle, "Backend iniciado!");
                                        }
                                    }
                                    tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                                        eprintln!("[backend-err] {}", String::from_utf8_lossy(&line));
                                    }
                                    tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                                        println!("[Aurity] Backend terminated: {:?}", status);
                                        break;
                                    }
                                    _ => {}
                                }
                            }
                        });

                        // Step 3: Wait for backend to be ready (health check)
                        emit_status(&app_handle, "Esperando que el backend responda...");

                        let mut attempts = 0;
                        let max_attempts = 60; // 30 seconds total (500ms * 60)

                        while attempts < max_attempts {
                            if check_backend_health(port).await {
                                state.is_ready.store(true, Ordering::SeqCst);
                                println!("[Aurity] Backend is healthy on port {}", port);
                                break;
                            }

                            attempts += 1;
                            sleep(Duration::from_millis(500)).await;

                            // Update status every 2 seconds
                            if attempts % 4 == 0 {
                                emit_status(
                                    &app_handle,
                                    &format!("Iniciando... {}s", attempts / 2),
                                );
                            }
                        }

                        // Step 4: Show main window or report error
                        if state.is_ready.load(Ordering::SeqCst) {
                            emit_status(&app_handle, "Listo!");

                            // Inject backend URL into main window
                            if let Some(main_window) = app_handle.get_webview_window("main") {
                                let js = format!(
                                    "window.__AURITY_BACKEND_URL__ = 'http://127.0.0.1:{}';",
                                    port
                                );
                                let _ = main_window.eval(&js);

                                // Show main window
                                let _ = main_window.show();
                                let _ = main_window.set_focus();
                            }

                            // Close splashscreen
                            if let Some(splash) = app_handle.get_webview_window("splashscreen") {
                                let _ = splash.close();
                            }

                            // Emit ready event
                            let _ = app_handle.emit("backend-ready", port);
                        } else {
                            emit_status(&app_handle, "Error: Backend no responde");
                            eprintln!(
                                "[Aurity] ERROR: Backend failed to respond after {} attempts",
                                max_attempts
                            );

                            // Show error in main window anyway
                            if let Some(main_window) = app_handle.get_webview_window("main") {
                                let _ = main_window.show();
                            }

                            let _ = app_handle.emit("backend-error", "Backend failed to start");
                        }
                    }
                    Err(e) => {
                        eprintln!("[Aurity] Failed to spawn sidecar: {}", e);
                        emit_status(&app_handle, &format!("Error: {}", e));
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_backend_status,
            check_ollama_status,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running Aurity Desktop");
}
