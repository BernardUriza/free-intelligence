use crate::state::*;
use serde::Serialize;
use std::future::Future;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri_plugin_shell::ShellExt;
use tokio::time::sleep;

#[derive(Serialize, Clone, Default)]
pub(crate) struct RagStats {
    gpu_memory_used_mb: u64,
    gpu_memory_total_mb: u64,
    gpu_device: String,
    model_name: String,
    embeddings_count: u64,
    avg_query_ms: f64,
    throughput_qps: f64,
}

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
            // Parse JSON to validate GPU presence
            match response.json::<HealthResponse>().await {
                Ok(health) => {
                    // Valid only if device is cuda/mps AND gpu_name exists
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
        Ok(_) => false,
        Err(_) => false,
    }
}

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

// ============================================================================
// Generic Sidecar Launcher (DRY helper)
// ============================================================================

async fn start_sidecar<F, Fut>(
    app_handle: &tauri::AppHandle,
    name: &str,
    args: &[&str],
    health_check: F,
    running_flag: &Mutex<bool>,
    process_pid: &Mutex<Option<u32>>,
) -> Result<bool, String>
where
    F: Fn() -> Fut,
    Fut: Future<Output = bool>,
{
    if health_check().await {
        *running_flag.lock().unwrap() = true;
        return Ok(true);
    }

    println!("[FI Monitor] Starting {} via sidecar...", name);

    let shell = app_handle.shell();
    let sidecar_cmd = shell
        .sidecar("fi-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?;

    let (mut rx, child) = sidecar_cmd
        .args(args)
        .spawn()
        .map_err(|e| format!("Failed to spawn {} sidecar: {}", name, e))?;

    let pid = child.pid();
    *process_pid.lock().unwrap() = Some(pid);

    let label = format!("fi-backend/{}", name.to_lowercase());
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                    println!("[{}] {}", label, String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    eprintln!("[{}] {}", label, String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                    println!("[{}] Terminated: {:?}", label, status);
                    break;
                }
                _ => {}
            }
        }
    });

    for _ in 0..30 {
        sleep(Duration::from_millis(500)).await;
        if health_check().await {
            *running_flag.lock().unwrap() = true;
            println!("[FI Monitor] {} started (PID: {})", name, pid);
            return Ok(true);
        }
    }
    Err(format!("{} started but not responding", name))
}

// Internal function (for auto-start and command)
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

// Internal function (for auto-start and command)
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

#[tauri::command]
pub(crate) async fn start_rag_service(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    start_rag_service_internal(&app_handle, state.inner().clone()).await
}

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

    // Parse stats from health endpoint
    Ok(RagStats {
        gpu_memory_used_mb: json["gpu_memory_mb"].as_u64().unwrap_or(0),
        gpu_memory_total_mb: 65536, // M1 Max default, adjust as needed
        gpu_device: json["device"].as_str().unwrap_or("unknown").to_string(),
        model_name: json["model"].as_str().unwrap_or("unknown").to_string(),
        embeddings_count: json["embeddings_count"].as_u64().unwrap_or(0),
        avg_query_ms: json["avg_query_ms"].as_f64().unwrap_or(0.0),
        throughput_qps: json["throughput_qps"].as_f64().unwrap_or(0.0),
    })
}

#[tauri::command]
pub(crate) async fn start_gateway(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    start_gateway_internal(&app_handle, state.inner().clone()).await
}

#[tauri::command]
pub(crate) async fn stop_gateway(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Gateway...");

    if let Some(pid) = state.gateway_process.lock().unwrap().take() {
        kill_process(pid);
    }

    *state.gateway_running.lock().unwrap() = false;
    Ok(true)
}
