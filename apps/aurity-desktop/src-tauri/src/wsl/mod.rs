// WSL (Windows Subsystem for Linux) Integration
//
// Provides Tauri commands for WSL lifecycle management:
//   Detection  → check_wsl_status() queries WSL distro/version
//   Install    → install_wsl(), enable_wsl_feature() with elevation
//   Backend    → setup/start/stop/health/logs for WSL-hosted backend
//   Paths      → Windows ↔ WSL path conversion utilities
//
// Module structure (SRP):
//   detection.rs — WSL availability and distro queries
//   install.rs   — WSL installation and feature enablement
//   backend.rs   — Backend lifecycle in WSL (setup, start, stop, health, logs)
//   paths.rs     — Path conversion and backend source discovery

pub mod backend;
pub mod detection;
pub mod install;
mod paths;

use serde::{Deserialize, Serialize};

// =============================================================================
// CONSTANTS
// =============================================================================

/// Default backend port — matches DEFAULT_BACKEND_PORT in main.rs.
/// WSL shares localhost with Windows, so the same port applies.
#[cfg(target_os = "windows")]
pub(crate) const WSL_BACKEND_PORT: u16 = 7001;

/// Health endpoint path (relative to backend root)
#[cfg(target_os = "windows")]
pub(crate) const HEALTH_ENDPOINT: &str = "/api/health";

/// Timeout for WSL backend health checks (seconds)
#[cfg(target_os = "windows")]
pub(crate) const WSL_HEALTH_TIMEOUT_SECS: u64 = 3;

/// Delay after starting backend before checking health (seconds)
#[cfg(target_os = "windows")]
pub(crate) const POST_START_DELAY_SECS: u64 = 2;

/// Default number of log lines to retrieve
#[cfg(target_os = "windows")]
pub(crate) const DEFAULT_LOG_LINES: u32 = 50;

/// Backend installation directory inside WSL
#[cfg(target_os = "windows")]
pub(crate) const WSL_BACKEND_DIR: &str = "/opt/aurity-backend";

/// Ollama host URL inside WSL (shares localhost with Windows)
#[cfg(target_os = "windows")]
pub(crate) const OLLAMA_HOST: &str = "http://localhost:11434";

// =============================================================================
// TYPES
// =============================================================================

/// WSL errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
#[allow(dead_code)] // Variants used only on Windows
pub enum WslError {
    #[error("WSL not available: {0}")]
    NotAvailable(String),
    #[error("Command failed: {0}")]
    CommandFailed(String),
    #[error("Setup error: {0}")]
    SetupError(String),
    #[error("Network error: {0}")]
    Network(String),
}

/// WSL installation status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WslStatus {
    pub installed: bool,
    pub distro: Option<String>,
    pub version: Option<u32>,
    pub backend_installed: bool,
    pub backend_running: bool,
}


