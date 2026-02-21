// Gateway — health check and lifecycle.

use std::sync::Arc;

use super::sidecar::start_sidecar;
use crate::state::*;

/// Check if the Gateway is running.
pub(crate) async fn check_gateway() -> bool {
    let Ok(client) = http_client(3) else {
        return false;
    };
    client
        .get(format!("{}/gateway/health", gateway_base_url()))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

/// Start the Gateway sidecar (used by auto-start and the Tauri command).
pub(crate) async fn start_gateway_internal(
    app_handle: &tauri::AppHandle,
    state: Arc<AppState>,
) -> Result<bool, String> {
    let port_str = GATEWAY_PORT.to_string();
    start_sidecar(
        app_handle,
        "Gateway",
        &["gateway", "--port", &port_str],
        || Box::pin(check_gateway()),
        &state.gateway_running,
        &state.gateway_process,
    )
    .await
}

/// Tauri command: start the Gateway.
#[tauri::command]
pub(crate) async fn start_gateway(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    start_gateway_internal(&app_handle, state.inner().clone()).await
}

/// Tauri command: stop the Gateway.
#[tauri::command]
pub(crate) async fn stop_gateway(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Gateway...");

    if let Some(pid) = state.gateway_process.lock().unwrap().take() {
        kill_process(pid);
    }

    *state.gateway_running.lock().unwrap() = false;
    Ok(true)
}
