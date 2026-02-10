use serde::{Deserialize, Serialize};
use std::process::Command;
use std::sync::Mutex;
use std::time::Duration;

// ============================================================================
// Service Port Constants (Single Source of Truth)
// ============================================================================

pub(crate) const OLLAMA_PORT: u16 = 11434;
pub(crate) const RAG_SERVICE_PORT: u16 = 11435;
pub(crate) const GATEWAY_PORT: u16 = 11400;

pub(crate) fn ollama_base_url() -> String {
    format!("http://localhost:{}", OLLAMA_PORT)
}

pub(crate) fn rag_service_base_url() -> String {
    format!("http://localhost:{}", RAG_SERVICE_PORT)
}

pub(crate) fn gateway_base_url() -> String {
    format!("http://localhost:{}", GATEWAY_PORT)
}

// ============================================================================
// Cross-platform Process Management
// ============================================================================

/// Kill a process by PID (cross-platform).
pub(crate) fn kill_process(pid: u32) {
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

/// Kill all processes matching a name (cross-platform fallback).
pub(crate) fn kill_process_by_name(name: &str) {
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", name])
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("pkill").arg(name).output();
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub(crate) enum TunnelMode {
    #[default]
    Local,       // localhost:11400 directo (0ms latency)
    Cloudflared, // cloudflared tunnel real (acceso remoto)
}

#[derive(Serialize, Deserialize, Clone, Default)]
pub(crate) struct AppConfig {
    pub(crate) azure_sas_url: Option<String>,
    pub(crate) last_tunnel_url: Option<String>,
    pub(crate) last_upload_success: Option<String>,
    pub(crate) tunnel_port: Option<u16>,
}

impl AppConfig {
    pub(crate) fn get_tunnel_port(&self) -> u16 {
        self.tunnel_port.unwrap_or(GATEWAY_PORT)
    }
}

#[derive(Default)]
pub(crate) struct AppState {
    pub(crate) ollama_running: Mutex<bool>,
    pub(crate) ollama_process: Mutex<Option<u32>>,
    pub(crate) tunnel_running: Mutex<bool>,
    pub(crate) tunnel_url: Mutex<Option<String>>,
    pub(crate) tunnel_process: Mutex<Option<u32>>,
    pub(crate) tunnel_mode: Mutex<TunnelMode>, // Track current tunnel type
    pub(crate) config: Mutex<AppConfig>,
    // Phase 3: GPU acceleration services
    pub(crate) rag_service_running: Mutex<bool>,
    pub(crate) rag_service_process: Mutex<Option<u32>>,
    pub(crate) gateway_running: Mutex<bool>,
    pub(crate) gateway_process: Mutex<Option<u32>>,
    // Watchdog state (prevents duplicate watchdog threads)
    pub(crate) watchdog_running: Mutex<bool>,
}

#[derive(Serialize, Clone)]
pub(crate) struct ServiceStatus {
    pub(crate) ollama_running: bool,
    pub(crate) ollama_models: Vec<String>,
    pub(crate) tunnel_running: bool,
    pub(crate) tunnel_url: Option<String>,
    pub(crate) rag_service_running: bool,
    pub(crate) gateway_running: bool,
    pub(crate) system_info: SystemInfo,
}

#[derive(Serialize, Clone, Default)]
pub(crate) struct SystemInfo {
    pub(crate) platform: String,
    pub(crate) hostname: String,
}

/// Build an HTTP client with a given timeout. Returns Err(String) on failure.
pub(crate) fn http_client(timeout_secs: u64) -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(timeout_secs))
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {}", e))
}
