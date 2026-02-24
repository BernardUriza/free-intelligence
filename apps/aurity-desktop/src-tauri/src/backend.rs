// Backend — sidecar lifecycle, port allocation, health checks, state.

use std::net::TcpListener;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::time::Duration;

use log::{error, info};
use tauri::{Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tokio::time::sleep;

use crate::constants::{
    BACKEND_HEALTH_TIMEOUT, DEFAULT_BACKEND_PORT, FALLBACK_PORT_END, FALLBACK_PORT_START,
    LOCALHOST, MAX_HEALTH_CHECK_ATTEMPTS,
};
use crate::window::{emit_status, setup_window_transition};

// =============================================================================
// STATE
// =============================================================================

/// Global state for backend
pub struct BackendState {
    pub port: AtomicU16,
    pub is_ready: AtomicBool,
}

impl BackendState {
    pub fn new() -> Self {
        Self {
            port: AtomicU16::new(0),
            is_ready: AtomicBool::new(false),
        }
    }
}

// =============================================================================
// PORT ALLOCATION
// =============================================================================

/// Find an available port based on build mode
/// Port allocation:
///   - DEFAULT_BACKEND_PORT: Desktop (fixed, both dev and release)
///   - FALLBACK_PORT_START..FALLBACK_PORT_END: Fallback if default is busy
fn find_available_port() -> Option<u16> {
    if TcpListener::bind((LOCALHOST, DEFAULT_BACKEND_PORT)).is_ok() {
        return Some(DEFAULT_BACKEND_PORT);
    }
    for p in FALLBACK_PORT_START..FALLBACK_PORT_END {
        if TcpListener::bind((LOCALHOST, p)).is_ok() {
            return Some(p);
        }
    }
    None
}

// =============================================================================
// HEALTH CHECKS
// =============================================================================

/// Check if the backend is responding to health checks.
/// Accepts a pre-built client to avoid recreating it on each call (used in retry loops).
async fn check_backend_health(client: &reqwest::Client, port: u16) -> bool {
    let url = format!("http://{}:{}/api/health", LOCALHOST, port);
    client
        .get(&url)
        .send()
        .await
        .is_ok_and(|r| r.status().is_success())
}

/// Run the health check loop, polling the backend until it responds or times out.
async fn run_health_checks(app_handle: &tauri::AppHandle, state: &Arc<BackendState>, port: u16) {
    emit_status(app_handle, "Verificando backend...");

    let mut attempts = 0;
    let health_client = reqwest::Client::builder()
        .timeout(BACKEND_HEALTH_TIMEOUT)
        .build()
        .unwrap_or_default();

    while attempts < MAX_HEALTH_CHECK_ATTEMPTS {
        if check_backend_health(&health_client, port).await {
            state.is_ready.store(true, Ordering::SeqCst);
            info!("Backend is healthy on port {}", port);

            let _ = app_handle.emit(
                "backend-ready",
                serde_json::json!({ "port": port }),
            );
            return;
        }

        attempts += 1;
        sleep(Duration::from_millis(500)).await;

        if attempts % 4 == 0 {
            emit_status(
                app_handle,
                &format!("Iniciando backend... {}s", attempts / 2),
            );
        }
    }

    emit_status(app_handle, "Error: El backend no responde después de 30 segundos. Puede que tu antivirus esté bloqueando la conexión local. Intenta reiniciar la aplicación.");
    error!("Backend failed to respond after {} attempts", MAX_HEALTH_CHECK_ATTEMPTS);
    let _ = app_handle.emit("backend-error", "El backend de IA no pudo iniciar. Verifica que tu antivirus no esté bloqueando Aurity y reinicia la aplicación.");
}

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Get the backend URL (with dynamic port)
#[tauri::command]
pub fn get_backend_url(state: tauri::State<'_, Arc<BackendState>>) -> String {
    let port = state.port.load(Ordering::SeqCst);
    format!("http://{}:{}", LOCALHOST, port)
}

/// Check if backend is ready
#[tauri::command]
pub fn get_backend_status(state: tauri::State<'_, Arc<BackendState>>) -> bool {
    state.is_ready.load(Ordering::SeqCst)
}

// =============================================================================
// SIDECAR LIFECYCLE
// =============================================================================

/// Spawn the backend sidecar and manage startup lifecycle:
/// 1. Find available port
/// 2. Spawn sidecar process with logging
/// 3. Setup window transition (splash → main)
/// 4. Run health checks
pub async fn spawn_backend(app_handle: tauri::AppHandle, state: Arc<BackendState>) {
    // Step 1: Find available port
    emit_status(&app_handle, "Buscando puerto disponible...");

    let port = match find_available_port() {
        Some(p) => {
            info!("Selected port {} for backend", p);
            p
        }
        None => {
            error!("No available ports in range {}-{}", DEFAULT_BACKEND_PORT, FALLBACK_PORT_END);
            emit_status(&app_handle, &format!("Error: No se encontró un puerto disponible ({}-{}). Cierra otras aplicaciones que puedan estar usando estos puertos e intenta de nuevo.", DEFAULT_BACKEND_PORT, FALLBACK_PORT_END));
            return;
        }
    };

    state.port.store(port, Ordering::SeqCst);

    // Step 2: Start the sidecar with the selected port
    emit_status(&app_handle, "Iniciando backend de IA...");

    let shell = app_handle.shell();
    let sidecar_cmd = match shell.sidecar("aurity-backend") {
        Ok(cmd) => cmd,
        Err(e) => {
            error!("Failed to create sidecar command: {}", e);
            emit_status(&app_handle, &classify_sidecar_error(&e.to_string()));
            return;
        }
    };
    let sidecar_result = sidecar_cmd
        .args(["--port", &port.to_string()])
        .spawn();

    match sidecar_result {
        Ok((mut rx, _child)) => {
            info!("Backend sidecar started");

            // Log sidecar output in background
            let status_handle = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                            let line_str = String::from_utf8_lossy(&line);
                            info!(target: "sidecar", "{}", line_str);

                            if line_str.contains("Uvicorn running")
                                || line_str.contains("Application startup complete")
                            {
                                emit_status(&status_handle, "Backend iniciado!");
                            }
                        }
                        tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                            error!(target: "sidecar", "{}", String::from_utf8_lossy(&line));
                        }
                        tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                            info!("Backend terminated: {:?}", status);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // Step 3: Setup splash → main window transition
            info!("Showing main window (backend starting in background)");
            setup_window_transition(&app_handle, port);

            // Step 4: Health check in background (non-blocking)
            run_health_checks(&app_handle, &state, port).await;
        }
        Err(e) => {
            error!("Failed to spawn sidecar: {}", e);
            emit_status(&app_handle, &classify_sidecar_error(&e.to_string()));

            // In dev mode, continue anyway without backend
            #[cfg(debug_assertions)]
            {
                info!("DEV MODE: Continuing without backend sidecar");
                sleep(Duration::from_secs(2)).await;
                emit_status(&app_handle, "Modo desarrollo (sin backend)");

                if let Some(main_window) = app_handle.get_webview_window("main") {
                    let js = format!(
                        "window.__AURITY_BACKEND_URL__ = 'http://{}:{}';",
                        LOCALHOST, port
                    );
                    let _ = main_window.eval(&js);
                    let _ = main_window.eval("window.__AURITY_DEV_MODE__ = true;");
                    let _ = main_window.show();
                    let _ = main_window.set_focus();
                }

                if let Some(splash) = app_handle.get_webview_window("splashscreen") {
                    let _ = splash.close();
                }
            }
        }
    }
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/// Classify sidecar errors into user-friendly Spanish messages.
fn classify_sidecar_error(err_str: &str) -> String {
    if err_str.contains("permission") || err_str.contains("denied") || err_str.contains("access") {
        format!(
            "Error de permisos: No se puede ejecutar el backend. \
             Verifica que tu antivirus no esté bloqueando Aurity \
             o intenta ejecutar como administrador. ({})",
            err_str
        )
    } else if err_str.contains("not found") || err_str.contains("No such file") {
        format!(
            "Error: No se encontró el ejecutable del backend. \
             La instalación puede estar incompleta. \
             Reinstala Aurity Desktop. ({})",
            err_str
        )
    } else {
        format!(
            "No se pudo iniciar el backend de IA: {}. \
             Intenta reiniciar la aplicación o reinstalarla.",
            err_str
        )
    }
}
