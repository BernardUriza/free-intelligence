// RAG Service — health check, lifecycle, and stats.

use std::sync::Arc;

use super::sidecar::start_sidecar;
use super::RagStats;
use crate::state::*;

/// Check if the RAG Service is running with GPU acceleration.
pub(crate) async fn check_rag_service() -> bool {
    #[derive(serde::Deserialize)]
    struct HealthResponse {
        device: String,
        gpu_name: Option<String>,
    }

    let Ok(client) = http_client(3) else {
        return false;
    };

    match client
        .get(format!("{}/rag/health", rag_service_base_url()))
        .send()
        .await
    {
        Ok(response) if response.status().is_success() => {
            match response.json::<HealthResponse>().await {
                Ok(health) => {
                    if (health.device == "cuda" || health.device == "mps")
                        && health.gpu_name.is_some()
                    {
                        println!(
                            "[FI Monitor] RAG Service GPU validated: {} on {}",
                            health.gpu_name.unwrap_or_default(),
                            health.device
                        );
                        true
                    } else {
                        println!(
                            "[FI Monitor] RAG Service running on CPU (device: {}) - rejecting",
                            health.device
                        );
                        false
                    }
                }
                Err(e) => {
                    println!(
                        "[FI Monitor] Failed to parse RAG health response: {}",
                        e
                    );
                    false
                }
            }
        }
        _ => false,
    }
}

/// Start the RAG Service sidecar (used by auto-start and the Tauri command).
pub(crate) async fn start_rag_service_internal(
    app_handle: &tauri::AppHandle,
    state: Arc<AppState>,
) -> Result<bool, String> {
    let port_str = RAG_SERVICE_PORT.to_string();
    start_sidecar(
        app_handle,
        "RAG Service",
        &["rag", "--port", &port_str],
        || Box::pin(check_rag_service()),
        &state.rag_service_running,
        &state.rag_service_process,
    )
    .await
}

/// Tauri command: start the RAG Service.
#[tauri::command]
pub(crate) async fn start_rag_service(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    start_rag_service_internal(&app_handle, state.inner().clone()).await
}

/// Tauri command: stop the RAG Service.
#[tauri::command]
pub(crate) async fn stop_rag_service(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    println!("[FI Monitor] Stopping RAG Service...");

    if let Some(pid) = state.rag_service_process.lock().unwrap().take() {
        kill_process(pid);
    }

    *state.rag_service_running.lock().unwrap() = false;
    Ok(true)
}

/// Tauri command: fetch RAG Service runtime stats.
#[tauri::command]
pub(crate) async fn get_rag_stats() -> Result<RagStats, String> {
    let client = http_client(5)?;
    let response = client
        .get(format!("{}/rag/health", rag_service_base_url()))
        .send()
        .await
        .map_err(|e| format!("Failed to fetch RAG stats: {}", e))?;

    if !response.status().is_success() {
        return Err(format!(
            "RAG Service returned error: {}",
            response.status()
        ));
    }

    let json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse RAG stats: {}", e))?;

    Ok(RagStats {
        gpu_memory_used_mb: json["gpu_memory_mb"].as_u64().unwrap_or(0),
        gpu_memory_total_mb: 65536,
        gpu_device: json["device"].as_str().unwrap_or("unknown").to_string(),
        model_name: json["model"].as_str().unwrap_or("unknown").to_string(),
        embeddings_count: json["embeddings_count"].as_u64().unwrap_or(0),
        avg_query_ms: json["avg_query_ms"].as_f64().unwrap_or(0.0),
        throughput_qps: json["throughput_qps"].as_f64().unwrap_or(0.0),
    })
}
