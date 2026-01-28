// FI Monitor - Ollama Tunnel Manager
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod ollama_installer;
mod python_installer;
mod setup_store;

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// Windows-specific constant for creating processes without console window
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tauri_plugin_updater::UpdaterExt;
use tokio::time::sleep;

// ============================================================================
// Configuration Persistence
// ============================================================================

#[derive(Serialize, Deserialize, Clone, Default)]
struct AppConfig {
    azure_sas_url: Option<String>,
    last_tunnel_url: Option<String>,
    last_upload_success: Option<String>,
    tunnel_port: Option<u16>,
}

impl AppConfig {
    fn get_tunnel_port(&self) -> u16 {
        self.tunnel_port.unwrap_or(11400)  // Default Gateway
    }
}

fn get_config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("config.json")
}

fn load_config() -> AppConfig {
    let path = get_config_path();
    if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        AppConfig::default()
    }
}

fn save_config(config: &AppConfig) -> Result<(), String> {
    let path = get_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Config saved to {:?}", path);
    Ok(())
}

fn get_app_lock_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("app.lock")
}

fn check_single_instance() {
    let lock_path = get_app_lock_path();

    if lock_path.exists() {
        // Read existing PID
        if let Ok(pid_str) = std::fs::read_to_string(&lock_path) {
            if let Ok(pid) = pid_str.trim().parse::<u32>() {
                // Check if process is still running
                #[cfg(target_os = "windows")]
                let running = {
                    use std::process::Command;
                    Command::new("tasklist")
                        .args(["/FI", &format!("PID eq {}", pid)])
                        .output()
                        .map(|output| String::from_utf8_lossy(&output.stdout).contains(&pid.to_string()))
                        .unwrap_or(false)
                };

                #[cfg(not(target_os = "windows"))]
                let running = {
                    use std::process::Command;
                    Command::new("kill")
                        .args(["-0", &pid.to_string()])
                        .status()
                        .map(|status| status.success())
                        .unwrap_or(false)
                };

                if running {
                    eprintln!("\n❌ ERROR: FI Monitor ya está corriendo (PID: {})", pid);
                    eprintln!("   Cierra la instancia actual antes de lanzar otra.\n");
                    eprintln!("   Comando para cerrar:");
                    #[cfg(target_os = "windows")]
                    eprintln!("   taskkill /F /PID {}\n", pid);
                    #[cfg(not(target_os = "windows"))]
                    eprintln!("   kill {}\n", pid);
                    std::process::exit(1);
                }
            }
        }
        // Stale lockfile, remove it
        let _ = std::fs::remove_file(&lock_path);
    }

    // Create lockfile with current PID
    let current_pid = std::process::id();
    if let Some(parent) = lock_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    std::fs::write(&lock_path, current_pid.to_string())
        .expect("Failed to create lockfile");

    println!("[FI Monitor] Single instance check passed (PID: {})", current_pid);
}

fn cleanup_lock() {
    let lock_path = get_app_lock_path();
    if lock_path.exists() {
        let _ = std::fs::remove_file(&lock_path);
    }
}

fn get_benchmarks_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("benchmarks.json")
}

fn load_benchmark_history() -> BenchmarkHistory {
    let path = get_benchmarks_path();
    if !path.exists() {
        return BenchmarkHistory { results: vec![] };
    }
    let content = std::fs::read_to_string(&path).unwrap_or_else(|_| "{}".to_string());
    serde_json::from_str(&content).unwrap_or(BenchmarkHistory { results: vec![] })
}

fn save_benchmark_result(result: BenchmarkSuite) -> Result<(), String> {
    let mut history = load_benchmark_history();
    history.results.insert(0, result); // Insert at front
    history.results.truncate(50); // Keep last 50

    let path = get_benchmarks_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&history).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Benchmark saved to {:?}", path);
    Ok(())
}

// ============================================================================
// App State
// ============================================================================

#[derive(Default)]
struct AppState {
    ollama_running: Mutex<bool>,
    tunnel_running: Mutex<bool>,
    tunnel_url: Mutex<Option<String>>,
    tunnel_process: Mutex<Option<u32>>,
    config: Mutex<AppConfig>,
    // Phase 3: GPU acceleration services
    rag_service_running: Mutex<bool>,
    rag_service_process: Mutex<Option<u32>>,
    gateway_running: Mutex<bool>,
    gateway_process: Mutex<Option<u32>>,
    // Watchdog state (prevents duplicate watchdog threads)
    watchdog_running: Mutex<bool>,
}

#[derive(Serialize, Clone)]
struct ServiceStatus {
    ollama_running: bool,
    ollama_models: Vec<String>,
    tunnel_running: bool,
    tunnel_url: Option<String>,
    rag_service_running: bool,
    gateway_running: bool,
    system_info: SystemInfo,
}

#[derive(Serialize, Clone, Default)]
struct SystemInfo {
    platform: String,
    hostname: String,
}

async fn check_ollama() -> bool {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap();
    client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

async fn get_ollama_models() -> Vec<String> {
    #[derive(Deserialize)]
    struct ModelsResponse {
        models: Vec<Model>,
    }
    #[derive(Deserialize)]
    struct Model {
        name: String,
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap();

    match client.get("http://localhost:11434/api/tags").send().await {
        Ok(response) => match response.json::<ModelsResponse>().await {
            Ok(r) => r.models.into_iter().map(|m| m.name).collect(),
            Err(_) => vec![],
        },
        Err(_) => vec![],
    }
}

// ============================================================================
// Model Management (Ollama API)
// ============================================================================

#[derive(Serialize, Clone)]
struct OllamaModelInfo {
    name: String,
    size: String,
    modified: String,
    digest: String,
}

fn format_size(bytes: u64) -> String {
    const GB: u64 = 1_073_741_824;
    const MB: u64 = 1_048_576;
    const KB: u64 = 1_024;

    if bytes >= GB {
        format!("{:.1} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.1} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.1} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}

fn format_time_ago(modified_at: &str) -> String {
    // Parse ISO 8601 timestamp and calculate time ago
    match chrono::DateTime::parse_from_rfc3339(modified_at) {
        Ok(dt) => {
            let now = chrono::Utc::now();
            let duration = now.signed_duration_since(dt);

            let days = duration.num_days();
            let hours = duration.num_hours();
            let minutes = duration.num_minutes();

            if days > 0 {
                if days == 1 {
                    "1 day ago".to_string()
                } else {
                    format!("{} days ago", days)
                }
            } else if hours > 0 {
                if hours == 1 {
                    "1 hour ago".to_string()
                } else {
                    format!("{} hours ago", hours)
                }
            } else if minutes > 0 {
                if minutes == 1 {
                    "1 minute ago".to_string()
                } else {
                    format!("{} minutes ago", minutes)
                }
            } else {
                "Just now".to_string()
            }
        }
        Err(_) => "Unknown".to_string(),
    }
}

#[tauri::command]
async fn list_ollama_models_detailed() -> Result<Vec<OllamaModelInfo>, String> {
    #[derive(Deserialize)]
    struct ModelsResponse {
        models: Vec<ModelDetail>,
    }

    #[derive(Deserialize)]
    struct ModelDetail {
        name: String,
        size: u64,
        modified_at: String,
        digest: String,
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let response = client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map_err(|e| format!("Failed to fetch models: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Ollama API returned {}", response.status()));
    }

    let data: ModelsResponse = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let models: Vec<OllamaModelInfo> = data
        .models
        .into_iter()
        .map(|m| OllamaModelInfo {
            name: m.name,
            size: format_size(m.size),
            modified: format_time_ago(&m.modified_at),
            digest: m.digest[..12].to_string(), // Short digest
        })
        .collect();

    Ok(models)
}

#[tauri::command]
async fn pull_ollama_model(model_name: String, app_handle: tauri::AppHandle) -> Result<(), String> {
    println!("[FI Monitor] Pulling model: {}", model_name);

    app_handle
        .emit("model-pull-started", model_name.clone())
        .map_err(|e| e.to_string())?;

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(600)) // 10 minutes
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    #[derive(Serialize)]
    struct PullRequest {
        name: String,
        stream: bool,
    }

    let response = client
        .post("http://localhost:11434/api/pull")
        .json(&PullRequest {
            name: model_name.clone(),
            stream: false,
        })
        .send()
        .await
        .map_err(|e| format!("Failed to pull model: {}", e))?;

    if response.status().is_success() {
        println!("[FI Monitor] ✅ Model pulled successfully: {}", model_name);
        app_handle
            .emit("model-pull-completed", model_name)
            .map_err(|e| e.to_string())?;
        Ok(())
    } else {
        let error_msg = format!("Pull failed with status: {}", response.status());
        println!("[FI Monitor] ❌ {}", error_msg);
        app_handle
            .emit("model-pull-failed", error_msg.clone())
            .map_err(|e| e.to_string())?;
        Err(error_msg)
    }
}

#[tauri::command]
async fn delete_ollama_model(model_name: String) -> Result<(), String> {
    println!("[FI Monitor] Deleting model: {}", model_name);

    let client = reqwest::Client::new();

    #[derive(Serialize)]
    struct DeleteRequest {
        name: String,
    }

    let response = client
        .delete("http://localhost:11434/api/delete")
        .json(&DeleteRequest {
            name: model_name.clone(),
        })
        .send()
        .await
        .map_err(|e| format!("Failed to delete model: {}", e))?;

    if response.status().is_success() {
        println!("[FI Monitor] ✅ Model deleted successfully: {}", model_name);
        Ok(())
    } else {
        let error_msg = format!("Delete failed with status: {}", response.status());
        println!("[FI Monitor] ❌ {}", error_msg);
        Err(error_msg)
    }
}

// ============================================================================
// Environment Variables Management
// ============================================================================

#[derive(Serialize, Deserialize, Clone)]
struct EnvVar {
    key: String,
    value: String,
}

fn get_env_file_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("ollama.env")
}

#[tauri::command]
fn get_env_vars() -> Result<Vec<EnvVar>, String> {
    let env_path = get_env_file_path();

    if !env_path.exists() {
        // Return defaults if file doesn't exist
        return Ok(vec![
            EnvVar { key: "OLLAMA_NUM_PARALLEL".to_string(), value: "1".to_string() },
            EnvVar { key: "OLLAMA_MAX_LOADED_MODELS".to_string(), value: "1".to_string() },
            EnvVar { key: "OLLAMA_ORIGINS".to_string(), value: "*".to_string() },
        ]);
    }

    let content = std::fs::read_to_string(&env_path)
        .map_err(|e| format!("Failed to read env file: {}", e))?;

    let vars: Vec<EnvVar> = content
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.starts_with('#'))
        .filter_map(|line| {
            let parts: Vec<&str> = line.splitn(2, '=').collect();
            if parts.len() == 2 {
                Some(EnvVar {
                    key: parts[0].trim().to_string(),
                    value: parts[1].trim().to_string(),
                })
            } else {
                None
            }
        })
        .collect();

    Ok(vars)
}

#[tauri::command]
fn set_env_vars(vars: Vec<EnvVar>) -> Result<(), String> {
    let env_path = get_env_file_path();

    if let Some(parent) = env_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config dir: {}", e))?;
    }

    let mut content = String::from("# Ollama Environment Variables\n");
    content.push_str("# Generated by FI Monitor\n\n");

    for var in vars {
        content.push_str(&format!("{}={}\n", var.key, var.value));
    }

    std::fs::write(&env_path, content)
        .map_err(|e| format!("Failed to write env file: {}", e))?;

    println!("[FI Monitor] ✅ Environment variables saved to {:?}", env_path);
    Ok(())
}

#[tauri::command]
async fn start_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_ollama().await {
        *state.ollama_running.lock().unwrap() = true;
        return Ok(true);
    }
    println!("[FI Monitor] Starting Ollama...");
    let result = Command::new("ollama")
        .arg("serve")
        .env("OLLAMA_ORIGINS", "*")
        .env("OLLAMA_HOST", "0.0.0.0:11434")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
    match result {
        Ok(_) => {
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_ollama().await {
                    *state.ollama_running.lock().unwrap() = true;
                    println!("[FI Monitor] Ollama started");
                    return Ok(true);
                }
            }
            Err("Ollama started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start Ollama: {}", e)),
    }
}

#[tauri::command]
async fn stop_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Ollama...");
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", "ollama.exe"])
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("pkill").arg("ollama").output();
    }
    *state.ollama_running.lock().unwrap() = false;
    Ok(true)
}

// ============================================================================
// RAG Service & Gateway Commands (Phase 3 - GPU Acceleration)
// ============================================================================

async fn check_rag_service() -> bool {
    #[derive(serde::Deserialize)]
    struct HealthResponse {
        device: String,
        gpu_name: Option<String>,
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap();

    match client.get("http://localhost:11435/rag/health").send().await {
        Ok(response) if response.status().is_success() => {
            // Parse JSON to validate GPU presence
            match response.json::<HealthResponse>().await {
                Ok(health) => {
                    // Valid only if device is cuda/mps AND gpu_name exists
                    if (health.device == "cuda" || health.device == "mps") && health.gpu_name.is_some() {
                        println!(
                            "[FI Monitor] ✅ RAG Service GPU validated: {} on {}",
                            health.gpu_name.unwrap_or_default(),
                            health.device
                        );
                        true
                    } else {
                        println!(
                            "[FI Monitor] ❌ RAG Service running on CPU (device: {}) - rejecting",
                            health.device
                        );
                        false
                    }
                }
                Err(e) => {
                    println!("[FI Monitor] ⚠️ Failed to parse RAG health response: {}", e);
                    false
                }
            }
        }
        Ok(_) => false,
        Err(_) => false,
    }
}

async fn check_gateway() -> bool {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap();
    client
        .get("http://localhost:11400/gateway/health")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

#[tauri::command]
async fn start_rag_service(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_rag_service().await {
        *state.rag_service_running.lock().unwrap() = true;
        return Ok(true);
    }

    println!("[FI Monitor] Starting RAG Service...");

    // Find Python executable
    let python = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    // Get the app directory (where gateway/ and rag_service/ are located)
    let app_dir =
        std::env::current_dir().map_err(|e| format!("Failed to get current dir: {}", e))?;

    println!("[FI Monitor] App directory: {:?}", app_dir);

    #[cfg(target_os = "windows")]
    let mut cmd = {
        let mut command = Command::new(python);
        command
            .args([
                "-m",
                "uvicorn",
                "rag_service.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "11435",
            ])
            .current_dir(&app_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(0x08000000); // CREATE_NO_WINDOW
        command
    };

    #[cfg(not(target_os = "windows"))]
    let mut cmd = {
        let mut command = Command::new(python);
        command
            .args([
                "-m",
                "uvicorn",
                "rag_service.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "11435",
            ])
            .current_dir(&app_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        command
    };

    let result = cmd.spawn();

    match result {
        Ok(child) => {
            let pid = child.id();
            *state.rag_service_process.lock().unwrap() = Some(pid);

            // Wait for service to be ready
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_rag_service().await {
                    *state.rag_service_running.lock().unwrap() = true;
                    println!("[FI Monitor] ✅ RAG Service started (PID: {})", pid);
                    return Ok(true);
                }
            }
            Err("RAG Service started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start RAG Service: {}", e)),
    }
}

#[tauri::command]
async fn stop_rag_service(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping RAG Service...");

    if let Some(pid) = state.rag_service_process.lock().unwrap().take() {
        #[cfg(target_os = "windows")]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/PID", &pid.to_string()])
                .output();
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = Command::new("kill").arg(pid.to_string()).output();
        }
    }

    *state.rag_service_running.lock().unwrap() = false;
    Ok(true)
}

#[tauri::command]
async fn start_gateway(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_gateway().await {
        *state.gateway_running.lock().unwrap() = true;
        return Ok(true);
    }

    println!("[FI Monitor] Starting Gateway...");

    // Find Python executable
    let python = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    // Get the app directory
    let app_dir =
        std::env::current_dir().map_err(|e| format!("Failed to get current dir: {}", e))?;

    #[cfg(target_os = "windows")]
    let mut cmd = {
        let mut command = Command::new(python);
        command
            .args([
                "-m",
                "uvicorn",
                "gateway.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "11400",
            ])
            .current_dir(&app_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(0x08000000); // CREATE_NO_WINDOW
        command
    };

    #[cfg(not(target_os = "windows"))]
    let mut cmd = {
        let mut command = Command::new(python);
        command
            .args([
                "-m",
                "uvicorn",
                "gateway.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "11400",
            ])
            .current_dir(&app_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        command
    };

    let result = cmd.spawn();

    match result {
        Ok(child) => {
            let pid = child.id();
            *state.gateway_process.lock().unwrap() = Some(pid);

            // Wait for service to be ready
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_gateway().await {
                    *state.gateway_running.lock().unwrap() = true;
                    println!("[FI Monitor] ✅ Gateway started (PID: {})", pid);
                    return Ok(true);
                }
            }
            Err("Gateway started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start Gateway: {}", e)),
    }
}

#[tauri::command]
async fn stop_gateway(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Gateway...");

    if let Some(pid) = state.gateway_process.lock().unwrap().take() {
        #[cfg(target_os = "windows")]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/PID", &pid.to_string()])
                .output();
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = Command::new("kill").arg(pid.to_string()).output();
        }
    }

    *state.gateway_running.lock().unwrap() = false;
    Ok(true)
}

#[tauri::command]
async fn start_tunnel(
    app: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<String, String> {
    start_tunnel_internal(app, Arc::clone(&*state)).await
}

#[tauri::command]
async fn stop_tunnel(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping tunnel...");
    if let Some(pid) = state.tunnel_process.lock().unwrap().take() {
        #[cfg(target_os = "windows")]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/PID", &pid.to_string()])
                .output();
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = Command::new("kill").arg(pid.to_string()).output();
        }
    }
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", "cloudflared.exe"])
            .output();
    }
    *state.tunnel_running.lock().unwrap() = false;
    *state.tunnel_url.lock().unwrap() = None;
    Ok(true)
}

/// Upload tunnel URL to Azure Blob Storage with retry logic
fn upload_tunnel_url_to_azure(url: &str, config: &AppConfig) -> Result<(), String> {
    // Get SAS URL from config (persisted) or environment
    let azure_sas_url = config
        .azure_sas_url
        .clone()
        .or_else(|| std::env::var("FI_AZURE_TUNNEL_BLOB_SAS").ok())
        .unwrap_or_default();

    if azure_sas_url.is_empty() {
        println!("[FI Monitor] No Azure SAS URL configured, skipping upload");
        // Still save locally as backup
        save_tunnel_url_locally(url)?;
        return Ok(());
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp,
        "version": "1.1",
        "services": {
            "ollama": format!("{}/api", url),
            "rag": format!("{}/rag", url),
            "gateway": format!("{}/gateway/health", url)
        }
    })
    .to_string();

    // Retry with exponential backoff
    let max_retries = 3;
    let mut last_error = String::new();

    for attempt in 0..max_retries {
        if attempt > 0 {
            let delay = Duration::from_millis(500 * 2u64.pow(attempt as u32));
            println!("[FI Monitor] Retry {} in {:?}...", attempt + 1, delay);
            std::thread::sleep(delay);
        }

        println!(
            "[FI Monitor] Uploading tunnel URL to Azure (attempt {})...",
            attempt + 1
        );

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| format!("Client error: {}", e))?;

        match client
            .put(&azure_sas_url)
            .header("x-ms-blob-type", "BlockBlob")
            .header("Content-Type", "application/json")
            .body(content.clone())
            .send()
        {
            Ok(response) if response.status().is_success() => {
                println!("[FI Monitor] ✅ Tunnel URL uploaded to Azure");
                // Also save locally as backup
                let _ = save_tunnel_url_locally(url);
                return Ok(());
            }
            Ok(response) => {
                last_error = format!(
                    "HTTP {}: {}",
                    response.status(),
                    response.status().canonical_reason().unwrap_or("Unknown")
                );
                println!("[FI Monitor] ⚠️ Azure returned: {}", last_error);
            }
            Err(e) => {
                last_error = format!("Request failed: {}", e);
                println!("[FI Monitor] ⚠️ {}", last_error);
            }
        }
    }

    // All retries failed - save locally as fallback
    println!(
        "[FI Monitor] ⚠️ Azure upload failed after {} retries, saving locally",
        max_retries
    );
    save_tunnel_url_locally(url)?;
    Err(last_error)
}

/// Save tunnel URL locally as backup
fn save_tunnel_url_locally(url: &str) -> Result<(), String> {
    let path = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("tunnel-url.json");

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp
    });

    let json = serde_json::to_string_pretty(&content).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] 💾 Tunnel URL saved locally: {:?}", path);
    Ok(())
}

/// Read the tunnel URL file content
#[tauri::command]
fn read_tunnel_file() -> Result<String, String> {
    let path = dirs::config_dir()
        .ok_or("Could not determine config directory")?
        .join("fi-monitor")
        .join("tunnel-url.json");

    // Verificar que el archivo existe
    if !path.exists() {
        return Err("Tunnel file not found. Start the tunnel to create it.".to_string());
    }

    // Leer contenido del archivo
    std::fs::read_to_string(&path).map_err(|e| format!("Failed to read file: {}", e))
}

/// Periodically re-upload tunnel URL to keep timestamp fresh
fn start_periodic_upload(url: String, config: AppConfig) {
    std::thread::spawn(move || {
        loop {
            // Wait 5 minutes
            std::thread::sleep(Duration::from_secs(300));

            println!("[FI Monitor] 🔄 Periodic re-upload of tunnel URL...");
            if let Err(e) = upload_tunnel_url_to_azure(&url, &config) {
                println!("[FI Monitor] ⚠️ Periodic upload failed: {}", e);
            }
        }
    });
}

/// Check if a process with given PID is still running
fn is_process_alive(pid: u32) -> bool {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        Command::new("tasklist")
            .args(["/FI", &format!("PID eq {}", pid), "/NH"])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
            .map(|output| {
                let stdout = String::from_utf8_lossy(&output.stdout);
                stdout.contains(&pid.to_string())
            })
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "windows"))]
    {
        Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
    }
}

/// Watchdog to monitor tunnel process and auto-restart if it dies
/// NOTE: This watchdog NEVER exits - it runs for the lifetime of the app
fn start_tunnel_watchdog(app: tauri::AppHandle, state: Arc<AppState>) {
    std::thread::spawn(move || {
        let mut restart_count = 0u32;
        let mut check_count = 0u32;
        println!("[FI Monitor Watchdog] Started (checking every 10s)");

        loop {
            // Check every 10 seconds (faster detection than 30s)
            std::thread::sleep(Duration::from_secs(10));
            check_count += 1;

            // Heartbeat log FIRST (every 6 checks = 60s)
            if check_count % 6 == 0 {
                println!("[FI Monitor Watchdog] Heartbeat #{}: woke up, checking state...", check_count);
            }

            let pid_opt = state.tunnel_process.lock().unwrap().clone();
            let tunnel_running = *state.tunnel_running.lock().unwrap();

            // Detailed state log after reading locks
            if check_count % 6 == 0 {
                println!("[FI Monitor Watchdog] State: tunnel_running={}, pid={:?}", tunnel_running, pid_opt);
            }

            if !tunnel_running {
                // Tunnel was manually stopped, keep watching for restart
                // DO NOT exit - watchdog must survive for app lifetime
                continue;
            }

            if let Some(pid) = pid_opt {
                if !is_process_alive(pid) {
                    restart_count += 1;
                    println!(
                        "[FI Monitor Watchdog] ⚠️ Tunnel process {} died! Restarting (attempt #{})...",
                        pid, restart_count
                    );

                    // Mark as not running
                    *state.tunnel_running.lock().unwrap() = false;
                    *state.tunnel_url.lock().unwrap() = None;

                    // Emit event
                    let _ = app.emit("tunnel-died", ());

                    // Wait a bit before restart
                    std::thread::sleep(Duration::from_secs(5));

                    // Trigger restart via command (this is async, so spawn it)
                    let app_clone = app.clone();
                    let state_clone = state.clone();
                    let attempt = restart_count;
                    tauri::async_runtime::spawn(async move {
                        // Re-check Ollama before restart
                        if check_ollama().await {
                            match start_tunnel_internal(app_clone.clone(), state_clone).await {
                                Ok(_) => println!("[FI Monitor Watchdog] ✅ Tunnel restarted (attempt #{})", attempt),
                                Err(e) => {
                                    println!("[FI Monitor Watchdog] ❌ Failed to restart (attempt #{}): {}", attempt, e)
                                }
                            }
                        } else {
                            println!("[FI Monitor Watchdog] ❌ Ollama not running, cannot restart tunnel (attempt #{})", attempt);
                        }
                    });

                    // DO NOT exit - continue monitoring
                    // Watchdog must survive for app lifetime to handle future crashes
                    continue;
                }
            }
        }
    });
}

/// Internal function to start tunnel (used by both command and watchdog)
async fn start_tunnel_internal(
    app: tauri::AppHandle,
    state: Arc<AppState>,
) -> Result<String, String> {
    if !check_ollama().await {
        return Err("Ollama is not running".to_string());
    }
    if *state.tunnel_running.lock().unwrap() {
        if let Some(url) = state.tunnel_url.lock().unwrap().clone() {
            return Ok(url);
        }
    }

    // Leer puerto configurado
    let tunnel_port = {
        let config = state.config.lock().unwrap();
        config.get_tunnel_port()
    };

    let tunnel_url = format!("http://localhost:{}", tunnel_port);
    println!("[FI Monitor] Starting Cloudflare tunnel to {}", tunnel_url);
    let cloudflared = find_cloudflared()?;

    #[cfg(target_os = "windows")]
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    #[cfg(target_os = "windows")]
    let mut child = Command::new(&cloudflared)
        .args(["tunnel", "--url", &tunnel_url])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;

    #[cfg(not(target_os = "windows"))]
    let mut child = Command::new(&cloudflared)
        .args(["tunnel", "--url", &tunnel_url])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;

    let pid = child.id();
    *state.tunnel_process.lock().unwrap() = Some(pid);
    *state.tunnel_running.lock().unwrap() = true;

    // Capture stderr in separate thread to find tunnel URL
    // IMPORTANT: Must .take() to move ownership to thread, otherwise stderr closes when child drops
    let stderr = child.stderr.take().expect("Failed to capture stderr");
    let state_clone = Arc::clone(&state);
    let app_clone = app.clone();
    let config = state.config.lock().unwrap().clone();

    // Move child into thread to keep it alive while reading stderr
    // Without this, child drops and stderr pipe closes before we can read URL
    std::thread::spawn(move || {
        // Keep child alive for the duration of this thread
        let _child_guard = child;
        let reader = BufReader::new(stderr);
        let url_regex = Regex::new(r"https://[a-z0-9-]+\.trycloudflare\.com").unwrap();

        for line in reader.lines().map_while(Result::ok) {
            println!("[cloudflared] {}", line);

            if let Some(url_match) = url_regex.find(&line) {
                let url = url_match.as_str().to_string();
                println!("[FI Monitor] ✅ Tunnel URL: {}", url);
                *state_clone.tunnel_url.lock().unwrap() = Some(url.clone());

                // Update config with last tunnel URL
                {
                    let mut cfg = state_clone.config.lock().unwrap();
                    cfg.last_tunnel_url = Some(url.clone());
                    let _ = save_config(&cfg);
                }

                // Emit event with URL
                let _ = app_clone.emit("tunnel-url-found", url.clone());
                let _ = app_clone.emit("tunnel-started", ());

                // Upload to Azure in background with retries
                let url_for_azure = url.clone();
                let config_for_upload = config.clone();
                std::thread::spawn(move || {
                    if let Err(e) = upload_tunnel_url_to_azure(&url_for_azure, &config_for_upload) {
                        println!("[FI Monitor] ⚠️ Azure upload failed: {}", e);
                    }
                });

                // Start periodic re-upload (every 5 minutes)
                start_periodic_upload(url.clone(), config.clone());

                // Start tunnel watchdog (auto-restart if it dies)
                // Only spawn watchdog ONCE (prevents duplicates on restart)
                let mut watchdog_lock = state_clone.watchdog_running.lock().unwrap();
                if !*watchdog_lock {
                    *watchdog_lock = true;
                    drop(watchdog_lock); // Release lock before spawning
                    start_tunnel_watchdog(app_clone.clone(), state_clone.clone());
                    println!("[FI Monitor] ✅ Tunnel watchdog spawned (will run for app lifetime)");
                } else {
                    println!("[FI Monitor] Watchdog already running (skipping duplicate spawn)");
                }

                break;
            }
        }

        // _child_guard drops here, but process continues running
        // (Rust Child has no Drop implementation - process is independent)
    });

    Ok("Tunnel starting... URL will appear when ready".to_string())
}

fn find_cloudflared() -> Result<String, String> {
    let candidates = vec![
        "cloudflared".to_string(),
        "C:\\cloudflared\\cloudflared.exe".to_string(),
        "C:\\Program Files\\cloudflared\\cloudflared.exe".to_string(),
    ];
    for path in candidates {
        if Command::new(&path).arg("--version").output().is_ok() {
            return Ok(path);
        }
    }
    Err("cloudflared not found".to_string())
}

#[tauri::command]
async fn get_status(state: tauri::State<'_, Arc<AppState>>) -> Result<ServiceStatus, String> {
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

#[tauri::command]
async fn test_ollama() -> Result<TestResult, String> {
    use std::time::Instant;
    if !check_ollama().await {
        return Err("Ollama no está ejecutándose".to_string());
    }
    let questions = vec![
        (
            "math",
            "¿Cuál es la raíz cuadrada de 144? Responde solo el número.",
        ),
        (
            "anatomy",
            "Explica brevemente qué es el hígado y su función principal.",
        ),
        (
            "math",
            "¿Cuál es la raíz cuadrada de 256? Responde solo el número.",
        ),
        (
            "anatomy",
            "Explica brevemente qué es el corazón y su función principal.",
        ),
        (
            "math",
            "¿Cuál es la raíz cuadrada de 625? Responde solo el número.",
        ),
        (
            "anatomy",
            "Explica brevemente qué son los pulmones y su función.",
        ),
    ];
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let idx = (now % questions.len() as u64) as usize;
    let (category, prompt) = questions[idx];
    println!("[FI Monitor] Testing: {}", prompt);
    let start = Instant::now();
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .unwrap();
    #[derive(Serialize)]
    struct Req {
        model: String,
        prompt: String,
        stream: bool,
    }
    #[derive(Deserialize)]
    struct Res {
        response: String,
    }
    let request = Req {
        model: "qwen3:1.7b".to_string(),
        prompt: prompt.to_string(),
        stream: false,
    };
    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Error: {}", e))?;
    let res: Res = response
        .json()
        .await
        .map_err(|e| format!("Parse error: {}", e))?;
    let elapsed_ms = start.elapsed().as_millis() as u64;
    println!("[FI Monitor] Response in {}ms", elapsed_ms);
    Ok(TestResult {
        category: category.to_string(),
        question: prompt.to_string(),
        answer: res.response.trim().to_string(),
        elapsed_ms,
        timestamp: chrono::Utc::now().to_rfc3339(),
    })
}

#[derive(Serialize, Clone)]
struct TestResult {
    category: String,
    question: String,
    answer: String,
    elapsed_ms: u64,
    timestamp: String,
}

// ============================================================================
// Benchmark Structures
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RagBenchmark {
    single_query_ms: u64,
    batch_10_ms: u64,
    batch_32_ms: u64,
    batch_100_ms: u64,
    throughput_qps: f64,
    gpu_memory_mb: f64,
    device: String,
    gpu_name: Option<String>,
    model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct OllamaBenchmark {
    single_query_ms: u64,
    batch_5_avg_ms: u64,
    tokens_per_sec: f64,
    model: String,
    eval_duration_ms: u64,
    eval_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GatewayBenchmark {
    health_check_ms: u64,
    routing_overhead_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BenchmarkSuite {
    timestamp: String,
    rag_service: Option<RagBenchmark>,
    ollama: Option<OllamaBenchmark>,
    gateway: Option<GatewayBenchmark>,
    total_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BenchmarkHistory {
    results: Vec<BenchmarkSuite>,
}

#[tauri::command]
async fn is_autostart_enabled(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())
}

#[tauri::command]
async fn enable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .enable()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}

#[tauri::command]
async fn disable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .disable()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}

// ============================================================================
// Config Commands
// ============================================================================

#[tauri::command]
async fn set_azure_sas_url(
    state: tauri::State<'_, Arc<AppState>>,
    sas_url: String,
) -> Result<bool, String> {
    let mut config = state.config.lock().unwrap();
    config.azure_sas_url = Some(sas_url);
    save_config(&config)?;
    println!("[FI Monitor] Azure SAS URL configured and saved");
    Ok(true)
}

#[tauri::command]
async fn get_azure_sas_url(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.azure_sas_url.clone())
}

#[tauri::command]
async fn get_last_tunnel_url(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.last_tunnel_url.clone())
}

#[tauri::command]
async fn set_tunnel_port(
    state: tauri::State<'_, Arc<AppState>>,
    port: u16,
) -> Result<(), String> {
    // Validación
    if port < 1024 {
        return Err("Port must be >= 1024 (system ports reserved)".to_string());
    }

    // Tunnel debe estar detenido
    if *state.tunnel_running.lock().unwrap() {
        return Err("Stop tunnel before changing port".to_string());
    }

    // Verificar puerto no en uso
    if is_port_in_use(port).await {
        return Err(format!("Port {} already in use", port));
    }

    // Guardar config
    let mut config = state.config.lock().unwrap();
    config.tunnel_port = Some(port);
    save_config(&config)?;

    println!("[FI Monitor] Tunnel port updated to {}", port);
    Ok(())
}

#[tauri::command]
async fn get_tunnel_port(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<u16, String> {
    let config = state.config.lock().unwrap();
    Ok(config.get_tunnel_port())
}

async fn is_port_in_use(port: u16) -> bool {
    use std::net::TcpListener;
    TcpListener::bind(("127.0.0.1", port)).is_err()
}

// ============================================================================
// Benchmark Commands
// ============================================================================

#[tauri::command]
async fn benchmark_rag_service() -> Result<RagBenchmark, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting RAG Service benchmark...");

    let api_key = std::env::var("RAG_API_KEY").unwrap_or_else(|_| "test-key".to_string());
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .unwrap();

    // 1. Health check - get GPU info
    #[derive(Deserialize)]
    struct HealthResponse {
        device: String,
        gpu_name: Option<String>,
        gpu_memory_mb: Option<f64>,
        model: String,
    }

    let health_resp = client
        .get("http://localhost:11435/rag/health")
        .send()
        .await
        .map_err(|e| format!("Health check failed: {}", e))?
        .json::<HealthResponse>()
        .await
        .map_err(|e| format!("Failed to parse health response: {}", e))?;

    #[derive(Serialize)]
    struct EmbedRequest {
        texts: Vec<String>,
    }

    // 2. Single query
    let start = Instant::now();
    let _ = client
        .post("http://localhost:11435/rag/embed")
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: vec!["Test embedding query".to_string()],
        })
        .send()
        .await
        .map_err(|e| format!("Single query failed: {}", e))?;
    let single_query_ms = start.elapsed().as_millis() as u64;

    // 3. Batch 10
    let start = Instant::now();
    let _ = client
        .post("http://localhost:11435/rag/embed")
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..10).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 10 failed: {}", e))?;
    let batch_10_ms = start.elapsed().as_millis() as u64;

    // 4. Batch 32
    let start = Instant::now();
    let _ = client
        .post("http://localhost:11435/rag/embed")
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..32).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 32 failed: {}", e))?;
    let batch_32_ms = start.elapsed().as_millis() as u64;

    // 5. Batch 100 + throughput
    let start = Instant::now();
    let _ = client
        .post("http://localhost:11435/rag/embed")
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..100).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 100 failed: {}", e))?;
    let batch_100_ms = start.elapsed().as_millis() as u64;
    let throughput_qps = (100.0 / (batch_100_ms as f64 / 1000.0)).round();

    println!("[FI Monitor] ✅ RAG Service benchmark complete");

    Ok(RagBenchmark {
        single_query_ms,
        batch_10_ms,
        batch_32_ms,
        batch_100_ms,
        throughput_qps,
        gpu_memory_mb: health_resp.gpu_memory_mb.unwrap_or(0.0),
        device: health_resp.device,
        gpu_name: health_resp.gpu_name,
        model: health_resp.model,
    })
}

#[tauri::command]
async fn benchmark_ollama() -> Result<OllamaBenchmark, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting Ollama benchmark...");

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .unwrap();

    #[derive(Serialize)]
    struct GenerateRequest {
        model: String,
        prompt: String,
        stream: bool,
    }

    #[derive(Deserialize)]
    struct GenerateResponse {
        response: String,
        #[serde(default)]
        eval_duration: u64,
        #[serde(default)]
        eval_count: u64,
    }

    // 1. Single query
    let start = Instant::now();
    let resp = client
        .post("http://localhost:11434/api/generate")
        .json(&GenerateRequest {
            model: "qwen3:1.7b".to_string(),
            prompt: "What is 2+2? Answer only the number.".to_string(),
            stream: false,
        })
        .send()
        .await
        .map_err(|e| format!("Single query failed: {}", e))?
        .json::<GenerateResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    let single_query_ms = start.elapsed().as_millis() as u64;

    let eval_duration_ms = resp.eval_duration / 1_000_000; // ns to ms
    let eval_count = resp.eval_count;

    // 2. Batch 5 queries (sequential)
    let mut total_ms = 0u64;
    for i in 0..5 {
        let start = Instant::now();
        let _ = client
            .post("http://localhost:11434/api/generate")
            .json(&GenerateRequest {
                model: "qwen3:1.7b".to_string(),
                prompt: format!("What is {}+{}? Answer only the number.", i, i),
                stream: false,
            })
            .send()
            .await
            .map_err(|e| format!("Batch query {} failed: {}", i, e))?;
        total_ms += start.elapsed().as_millis() as u64;
    }
    let batch_5_avg_ms = total_ms / 5;

    // 3. Calculate tokens/sec
    let tokens_per_sec = if eval_duration_ms > 0 {
        (eval_count as f64 / (eval_duration_ms as f64 / 1000.0)).round()
    } else {
        0.0
    };

    println!("[FI Monitor] ✅ Ollama benchmark complete");

    Ok(OllamaBenchmark {
        single_query_ms,
        batch_5_avg_ms,
        tokens_per_sec,
        model: "qwen3:1.7b".to_string(),
        eval_duration_ms,
        eval_count,
    })
}

#[tauri::command]
async fn benchmark_gateway() -> Result<GatewayBenchmark, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting Gateway benchmark...");

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .unwrap();

    // 1. Health check latency
    let start = Instant::now();
    let _ = client
        .get("http://localhost:11400/gateway/health")
        .send()
        .await
        .map_err(|e| format!("Gateway health check failed: {}", e))?;
    let health_check_ms = start.elapsed().as_millis() as u64;

    // 2. Routing overhead (gateway proxy vs direct)
    let start = Instant::now();
    let _ = client
        .get("http://localhost:11400/rag/health")
        .send()
        .await
        .map_err(|e| format!("Gateway proxy failed: {}", e))?;
    let gateway_proxy_ms = start.elapsed().as_millis() as u64;

    let start = Instant::now();
    let _ = client
        .get("http://localhost:11435/rag/health")
        .send()
        .await
        .map_err(|e| format!("Direct RAG health check failed: {}", e))?;
    let direct_ms = start.elapsed().as_millis() as u64;

    let routing_overhead_ms = gateway_proxy_ms as i64 - direct_ms as i64;

    println!("[FI Monitor] ✅ Gateway benchmark complete");

    Ok(GatewayBenchmark {
        health_check_ms,
        routing_overhead_ms,
    })
}

#[tauri::command]
async fn benchmark_all(app: tauri::AppHandle) -> Result<BenchmarkSuite, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting benchmark suite...");
    let suite_start = Instant::now();

    // 1. RAG Service
    let rag_service = match benchmark_rag_service().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] ⚠️ RAG Service skipped: {}", e);
            None
        }
    };

    // 2. Ollama
    let ollama = match benchmark_ollama().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] ⚠️ Ollama skipped: {}", e);
            None
        }
    };

    // 3. Gateway
    let gateway = match benchmark_gateway().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] ⚠️ Gateway skipped: {}", e);
            None
        }
    };

    let total_duration_ms = suite_start.elapsed().as_millis() as u64;

    let timestamp = chrono::Local::now().to_rfc3339();

    let suite = BenchmarkSuite {
        timestamp,
        rag_service,
        ollama,
        gateway,
        total_duration_ms,
    };

    // Save result
    save_benchmark_result(suite.clone())?;

    // Emit event
    let _ = app.emit("benchmark-complete", &suite);

    println!("[FI Monitor] ✅ Benchmark suite complete in {}ms", total_duration_ms);

    Ok(suite)
}

#[tauri::command]
async fn get_benchmark_history() -> Result<BenchmarkHistory, String> {
    Ok(load_benchmark_history())
}

fn main() {
    // Check for single instance FIRST (fail hard if already running)
    check_single_instance();

    // Setup cleanup on panic
    std::panic::set_hook(Box::new(move |panic_info| {
        cleanup_lock();
        eprintln!("FI Monitor panicked: {:?}", panic_info);
    }));

    // Load persisted config
    let config = load_config();
    println!("[FI Monitor] Config loaded from {:?}", get_config_path());
    if config.azure_sas_url.is_some() {
        println!("[FI Monitor] Azure SAS URL: configured ✓");
    }
    if let Some(ref url) = config.last_tunnel_url {
        println!("[FI Monitor] Last tunnel URL: {}", url);
    }

    let state = Arc::new(AppState {
        config: Mutex::new(config),
        ..Default::default()
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, Some(vec!["--minimized"])))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_clone = state.clone();

            // Setup system tray with Rust TrayIconBuilder
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "Show", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("FI Monitor")
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "quit" => app.exit(0),
                    "show" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event {
                        if let Some(w) = tray.app_handle().get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                })
                .build(app)?;

            // Intercept close to minimize to tray instead of quitting
            if let Some(window) = app.get_webview_window("main") {
                let window_clone = window.clone();
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = window_clone.hide();
                        println!("[FI Monitor] Window minimized to tray");
                    }
                });
            }

            // Check for updates in background
            let app_for_update = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking for updates...");
                match app_for_update.updater() {
                    Ok(updater) => {
                        match updater.check().await {
                            Ok(Some(update)) => {
                                println!("[FI Monitor] Update available: {} -> {}", update.current_version, update.version);
                                println!("[FI Monitor] Downloading and installing update...");

                                match update.download_and_install(|_, _| {}, || {}).await {
                                    Ok(_) => {
                                        println!("[FI Monitor] ✅ Update installed successfully! Restart required.");
                                        // Notify user (optional - could add notification here)
                                    }
                                    Err(e) => {
                                        println!("[FI Monitor] ⚠️ Failed to install update: {}", e);
                                    }
                                }
                            }
                            Ok(None) => {
                                println!("[FI Monitor] ✅ Already up to date");
                            }
                            Err(e) => {
                                println!("[FI Monitor] ⚠️ Failed to check for updates: {}", e);
                            }
                        }
                    }
                    Err(e) => {
                        println!("[FI Monitor] ⚠️ Failed to initialize updater: {}", e);
                    }
                }
            });

            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking services (with startup retry)...");
                // Retry logic for startup - Ollama might still be booting
                let mut attempts = 0;
                let max_attempts = 20; // 20 attempts × 1.5s = 30s max
                while attempts < max_attempts {
                    if check_ollama().await {
                        *state_clone.ollama_running.lock().unwrap() = true;
                        println!("[FI Monitor] ✅ Ollama running (attempt {})", attempts + 1);

                        // Phase 3: Auto-start RAG Service (GPU embeddings)
                        println!("[FI Monitor] Auto-starting RAG Service...");
                        if !check_rag_service().await {
                            let python = if cfg!(target_os = "windows") { "python" } else { "python3" };
                            let app_dir = std::env::current_dir().unwrap_or_default();

                            #[cfg(target_os = "windows")]
                            const CREATE_NO_WINDOW: u32 = 0x08000000;

                            #[cfg(target_os = "windows")]
                            let result = Command::new(python)
                                .args(["-m", "uvicorn", "rag_service.main:app", "--host", "0.0.0.0", "--port", "11435"])
                                .current_dir(&app_dir)
                                .stdout(Stdio::null())
                                .stderr(Stdio::null())
                                .creation_flags(CREATE_NO_WINDOW)
                                .spawn();

                            #[cfg(not(target_os = "windows"))]
                            let result = Command::new(python)
                                .args(["-m", "uvicorn", "rag_service.main:app", "--host", "0.0.0.0", "--port", "11435"])
                                .current_dir(&app_dir)
                                .stdout(Stdio::null())
                                .stderr(Stdio::null())
                                .spawn();

                            if let Ok(child) = result {
                                let pid = child.id();
                                *state_clone.rag_service_process.lock().unwrap() = Some(pid);
                                // Wait for RAG service to be ready
                                for _ in 0..20 {
                                    sleep(Duration::from_millis(500)).await;
                                    if check_rag_service().await {
                                        *state_clone.rag_service_running.lock().unwrap() = true;
                                        println!("[FI Monitor] ✅ RAG Service auto-started (PID: {})", pid);
                                        break;
                                    }
                                }
                            }
                        }

                        // Phase 3: Auto-start Gateway (HTTP router)
                        println!("[FI Monitor] Auto-starting Gateway...");
                        if !check_gateway().await {
                            let python = if cfg!(target_os = "windows") { "python" } else { "python3" };
                            let app_dir = std::env::current_dir().unwrap_or_default();

                            #[cfg(target_os = "windows")]
                            let result = Command::new(python)
                                .args(["-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "11400"])
                                .current_dir(&app_dir)
                                .stdout(Stdio::null())
                                .stderr(Stdio::null())
                                .creation_flags(CREATE_NO_WINDOW)
                                .spawn();

                            #[cfg(not(target_os = "windows"))]
                            let result = Command::new(python)
                                .args(["-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "11400"])
                                .current_dir(&app_dir)
                                .stdout(Stdio::null())
                                .stderr(Stdio::null())
                                .spawn();

                            if let Ok(child) = result {
                                let pid = child.id();
                                *state_clone.gateway_process.lock().unwrap() = Some(pid);
                                // Wait for gateway to be ready
                                for _ in 0..20 {
                                    sleep(Duration::from_millis(500)).await;
                                    if check_gateway().await {
                                        *state_clone.gateway_running.lock().unwrap() = true;
                                        println!("[FI Monitor] ✅ Gateway auto-started (PID: {})", pid);
                                        break;
                                    }
                                }
                            }
                        }

                        let _ = app_handle.emit("services-checked", ());

                        // Tunnel is NOT auto-started - user must activate manually
                        println!("[FI Monitor] ℹ️ Tunnel ready (manual activation required)");
                        return;
                    }
                    attempts += 1;
                    if attempts < max_attempts {
                        println!("[FI Monitor] ⏳ Ollama not ready, retrying ({}/{})...", attempts, max_attempts);
                        sleep(Duration::from_millis(1500)).await;
                    }
                }
                println!("[FI Monitor] ⚠️ Ollama not found after {} attempts", max_attempts);
                let _ = app_handle.emit("services-checked", ());
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_ollama,
            stop_ollama,
            start_rag_service,
            stop_rag_service,
            start_gateway,
            stop_gateway,
            start_tunnel,
            stop_tunnel,
            get_status,
            test_ollama,
            is_autostart_enabled,
            enable_autostart,
            disable_autostart,
            set_azure_sas_url,
            get_azure_sas_url,
            benchmark_rag_service,
            benchmark_ollama,
            benchmark_gateway,
            benchmark_all,
            get_benchmark_history,
            get_last_tunnel_url,
            set_tunnel_port,
            get_tunnel_port,
            read_tunnel_file,
            // Model Management
            list_ollama_models_detailed,
            pull_ollama_model,
            delete_ollama_model,
            // Environment Variables
            get_env_vars,
            set_env_vars,
            ollama_installer::check_ollama_installed,
            ollama_installer::install_ollama_silent,
            ollama_installer::download_and_install_ollama,
            python_installer::check_python_installed,
            python_installer::install_python_silent,
            python_installer::download_and_install_python,
            setup_store::get_setup_state,
            setup_store::update_setup_state,
            setup_store::mark_setup_completed,
            setup_store::mark_setup_skipped,
        ])
        .run(tauri::generate_context!())
        .expect("error running FI Monitor");

    // Cleanup on normal exit
    cleanup_lock();
}
