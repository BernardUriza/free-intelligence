// FI Monitor Integration Module
//
// Handles detection, download, installation, and launching of FI Monitor
// for cloud connectivity and tunnel management.
//
// Module structure (SRP):
//   paths.rs     — Executable/installer filenames, URLs, install path discovery
//   detection.rs — Check installed status, running process, registry version
//   download.rs  — Stream installer from GitHub Releases with progress events
//   install.rs   — Silent NSIS install, full orchestration flow, launch
//   errors.rs    — User-friendly error classification (network/HTTP/NSIS)

pub mod detection;
pub mod download;
mod errors;
pub mod install;
mod paths;

use serde::Serialize;
use std::time::Duration;

// =============================================================================
// CONSTANTS
// =============================================================================

/// GitHub repository owner/name — single source of truth for release URLs.
/// The updater endpoint in tauri.conf.json uses the same repo.
pub(crate) const GITHUB_REPO_OWNER: &str = "BernardUriza";
pub(crate) const GITHUB_REPO_NAME: &str = "free-intelligence";

/// HTTP timeout for downloading the installer
pub(crate) const DOWNLOAD_TIMEOUT: Duration = Duration::from_secs(120);

/// Delay after silent install before verifying success
pub(crate) const POST_INSTALL_DELAY: Duration = Duration::from_secs(2);

/// Maximum time to wait for the NSIS installer to complete
pub(crate) const INSTALL_TIMEOUT: Duration = Duration::from_secs(300); // 5 minutes

/// NSIS exit code for "Access Denied"
pub(crate) const NSIS_EXIT_ACCESS_DENIED: i32 = 5;

/// Injected at build time from apps/fi-monitor/src-tauri/tauri.conf.json by build.rs
pub(crate) const FI_MONITOR_VERSION: &str = env!("FI_MONITOR_VERSION");
pub(crate) const FI_MONITOR_PRODUCT_NAME: &str = env!("FI_MONITOR_PRODUCT_NAME");

// =============================================================================
// TYPES
// =============================================================================

/// Monitor errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
pub enum MonitorError {
    #[error("Not installed: {0}")]
    NotInstalled(String),
    #[error("Download failed: {0}")]
    DownloadFailed(String),
    #[error("Install failed: {0}")]
    InstallFailed(String),
    #[error("IO error: {0}")]
    Io(String),
}

/// Status of FI Monitor installation and runtime
#[derive(Serialize)]
pub struct FiMonitorStatus {
    pub installed: bool,
    pub running: bool,
    pub version: Option<String>,
    pub install_path: Option<String>,
}

/// Download progress info
#[derive(Clone, Serialize)]
pub struct DownloadProgress {
    pub downloaded_bytes: u64,
    pub total_bytes: u64,
    pub percentage: f32,
}


