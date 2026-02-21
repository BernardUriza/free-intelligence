// Service status aggregation.

use std::sync::Arc;

use crate::ollama::{check_ollama, get_ollama_models};
use crate::services::{check_gateway, check_rag_service};
use crate::state::*;

/// Query all services and return aggregated status.
#[tauri::command]
pub(crate) async fn get_status(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<ServiceStatus, String> {
    let ollama_running = check_ollama().await;
    let models = if ollama_running {
        get_ollama_models().await
    } else {
        vec![]
    };
    let rag_service_running = check_rag_service().await;
    let gateway_running = check_gateway().await;

    *state.ollama_running.lock().unwrap() = ollama_running;
    *state.rag_service_running.lock().unwrap() = rag_service_running;
    *state.gateway_running.lock().unwrap() = gateway_running;

    Ok(ServiceStatus {
        ollama_running,
        ollama_models: models,
        tunnel_running: *state.tunnel_running.lock().unwrap(),
        tunnel_url: state.tunnel_url.lock().unwrap().clone(),
        rag_service_running,
        gateway_running,
        system_info: SystemInfo {
            platform: std::env::consts::OS.to_string(),
            hostname: gethostname::gethostname().to_string_lossy().to_string(),
        },
    })
}
