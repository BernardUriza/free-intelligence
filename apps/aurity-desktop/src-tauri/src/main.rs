// Aurity Desktop - Main Entry Point
//
// This application manages:
// 1. FastAPI backend as a sidecar process with DYNAMIC port allocation
// 2. Tauri webview for the frontend
// 3. Splashscreen while loading
// 4. Health checks before showing UI
// 5. Proper lifecycle management (cleanup on exit)
// 6. First-run config bootstrap (extracts templates to user data dir)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod auth;
mod templates;

use auth::AuthState;
use serde::Serialize;
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tauri::{Emitter, Manager};
use tauri_plugin_deep_link::DeepLinkExt;
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

/// First-run status for frontend wizard
#[derive(Serialize)]
struct FirstRunStatus {
    config_initialized: bool,
    ollama_available: bool,
    data_dir: String,
}

/// Check first-run status (for frontend wizard)
#[tauri::command]
async fn check_first_run_status(app: tauri::AppHandle) -> Result<FirstRunStatus, String> {
    let data_dir = get_data_dir(&app)?;
    let config_exists = data_dir.join("config/fi.policy.yaml").exists();

    // Check Ollama synchronously for simplicity
    let ollama_ok = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    Ok(FirstRunStatus {
        config_initialized: config_exists,
        ollama_available: ollama_ok,
        data_dir: data_dir.to_string_lossy().to_string(),
    })
}

/// Get the user data directory for Aurity
fn get_data_dir(_app: &tauri::AppHandle) -> Result<PathBuf, String> {
    // Use ~/.aurity for consistency with backend expectations
    // Note: _app parameter kept for potential future use with tauri::PathResolver
    let home = dirs::home_dir().ok_or("Could not find home directory")?;
    Ok(home.join(".aurity"))
}

/// Atomically write a file: write to .tmp, then rename
/// This prevents partial writes and is safer against TOCTOU attacks
fn atomic_write(path: &PathBuf, content: &[u8]) -> Result<(), String> {
    let tmp_path = path.with_extension("tmp");

    // Write to temporary file
    fs::write(&tmp_path, content)
        .map_err(|e| format!("Failed to write temp file {:?}: {}", tmp_path, e))?;

    // Atomically rename to final path
    fs::rename(&tmp_path, path)
        .map_err(|e| format!("Failed to rename {:?} to {:?}: {}", tmp_path, path, e))?;

    Ok(())
}

/// Validate filename doesn't contain path separators (security check)
fn is_safe_filename(filename: &str) -> bool {
    !filename.contains('/') && !filename.contains('\\') && !filename.contains("..")
}

/// Bootstrap configuration files on first run
/// Extracts embedded templates to user data directory
///
/// Security measures:
/// - Atomic writes (write to .tmp, then rename) to prevent partial state
/// - Filename validation to prevent path traversal
/// - Symlink detection to prevent symlink attacks
fn bootstrap_config(app: &tauri::AppHandle) -> Result<bool, String> {
    let data_dir = get_data_dir(app)?;
    let config_dir = data_dir.join("config");
    let personas_dir = config_dir.join("personas");
    let storage_dir = data_dir.join("storage");
    let policy_path = config_dir.join("fi.policy.yaml");

    // Check if already initialized (atomic check - file either exists or doesn't)
    if policy_path.exists() {
        // Additional safety: verify it's a regular file, not a symlink
        if policy_path.is_symlink() {
            return Err("Security: config file is a symlink, refusing to proceed".to_string());
        }
        println!("[Aurity] Config already initialized at {:?}", config_dir);
        return Ok(false); // Not first run
    }

    println!("[Aurity] First run detected - bootstrapping config to {:?}", data_dir);

    // Create directories (these are idempotent operations)
    fs::create_dir_all(&config_dir).map_err(|e| format!("Failed to create config dir: {}", e))?;
    fs::create_dir_all(&personas_dir).map_err(|e| format!("Failed to create personas dir: {}", e))?;
    fs::create_dir_all(&storage_dir).map_err(|e| format!("Failed to create storage dir: {}", e))?;

    // Verify directories are not symlinks (security check)
    if config_dir.is_symlink() || personas_dir.is_symlink() || storage_dir.is_symlink() {
        return Err("Security: one or more config directories are symlinks".to_string());
    }

    // Write all persona templates first (so policy is written last as completion marker)
    for (filename, content) in templates::PERSONAS {
        // Validate filename to prevent path traversal
        if !is_safe_filename(filename) {
            return Err(format!("Security: invalid filename in templates: {}", filename));
        }
        let persona_path = personas_dir.join(filename);
        atomic_write(&persona_path, content.as_bytes())?;
    }

    // Write policy template LAST (serves as "initialization complete" marker)
    atomic_write(&policy_path, templates::POLICY.as_bytes())?;

    println!("[Aurity] Config bootstrapped successfully!");
    println!("[Aurity]   - Policy: {:?}", policy_path);
    println!("[Aurity]   - Personas: {} files", templates::PERSONAS.len());

    Ok(true) // First run completed
}

fn main() {
    let backend_state = Arc::new(BackendState {
        port: AtomicU16::new(0),
        is_ready: AtomicBool::new(false),
    });

    let auth_state = AuthState::default();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_deep_link::init())
        // Note: single-instance plugin removed due to Tauri 2.x config issues
        // Deep links on macOS handled via on_open_url() below, Windows/Linux can add back later
        .plugin(tauri_plugin_opener::init())
        .manage(backend_state.clone())
        .manage(auth_state)
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state = backend_state.clone();

            // Register deep link handler for OAuth callbacks (macOS)
            #[cfg(target_os = "macos")]
            {
                let dl_handle = app_handle.clone();
                app.deep_link().on_open_url(move |event| {
                    for url in event.urls() {
                        let url_str = url.to_string();
                        if url_str.starts_with("aurity://") {
                            println!("[Aurity] Deep link received: {}", url_str);
                            let _ = dl_handle.emit("deep-link-received", url_str);
                        }
                    }
                });
            }

            // On Linux/Windows, check CLI args for deep link (first launch)
            #[cfg(not(target_os = "macos"))]
            {
                for arg in std::env::args() {
                    if arg.starts_with("aurity://") {
                        println!("[Aurity] Deep link from args: {}", arg);
                        let _ = app_handle.emit("deep-link-received", arg);
                    }
                }
            }

            // Step 0: Bootstrap config on first run (BEFORE spawning backend)
            emit_status(&app_handle, "Verificando configuración...");
            match bootstrap_config(&app_handle) {
                Ok(true) => {
                    println!("[Aurity] First run - config bootstrapped");
                    let _ = app_handle.emit("first-run-detected", ());
                }
                Ok(false) => {
                    println!("[Aurity] Config already exists");
                }
                Err(e) => {
                    eprintln!("[Aurity] WARNING: Failed to bootstrap config: {}", e);
                    // Continue anyway - backend might still work
                }
            }

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
                    .env("DESKTOP_OFFLINE", "1") // Enable offline auth bypass for desktop
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
            check_first_run_status,
            // Auth0 OAuth commands
            auth::configure_auth0,
            auth::start_auth_flow,
            auth::handle_auth_callback,
            auth::get_stored_tokens,
            auth::refresh_tokens,
            auth::clear_tokens,
            auth::is_token_expired,
            auth::get_token_expiry,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running Aurity Desktop");
}
