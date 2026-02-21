// FI Monitor Integration Module
//
// Handles detection, download, installation, and launching of FI Monitor
// for cloud connectivity and tunnel management.
//
// Architecture:
//   Detection  → find_installed_path() checks known install locations
//   Download   → download_fi_monitor() streams from GitHub Releases
//   Install    → install_fi_monitor_silent() runs NSIS /S
//   Orchestr.  → install_fi_monitor_full() chains download → install → launch

use log::{info, warn};
use serde::Serialize;
use std::path::PathBuf;
use std::time::Duration;

// =============================================================================
// CONSTANTS
// =============================================================================

/// GitHub repository owner/name — single source of truth for release URLs.
/// The updater endpoint in tauri.conf.json uses the same repo.
const GITHUB_REPO_OWNER: &str = "BernardUriza";
const GITHUB_REPO_NAME: &str = "free-intelligence";

/// HTTP timeout for downloading the installer
const DOWNLOAD_TIMEOUT: Duration = Duration::from_secs(120);

/// Seconds to wait after silent install before verifying
const POST_INSTALL_DELAY: Duration = Duration::from_secs(2);

/// NSIS exit code for "Access Denied"
const NSIS_EXIT_ACCESS_DENIED: i32 = 5;

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

/// Injected at build time from apps/fi-monitor/src-tauri/tauri.conf.json by build.rs
const FI_MONITOR_VERSION: &str = env!("FI_MONITOR_VERSION");
const FI_MONITOR_PRODUCT_NAME: &str = env!("FI_MONITOR_PRODUCT_NAME");

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

/// Executable filename derived from productName (Tauri NSIS renames binary to this)
fn exe_name() -> String {
    format!("{}.exe", FI_MONITOR_PRODUCT_NAME)
}

/// NSIS installer filename: {productName}_{version}_x64-setup.exe
fn installer_filename() -> String {
    format!(
        "{}_{}_x64-setup.exe",
        FI_MONITOR_PRODUCT_NAME, FI_MONITOR_VERSION
    )
}

/// GitHub Releases download URL for the current FI Monitor version
fn release_download_url() -> String {
    format!(
        "https://github.com/{}/{}/releases/download/v{}/{}",
        GITHUB_REPO_OWNER, GITHUB_REPO_NAME, FI_MONITOR_VERSION, installer_filename()
    )
}

/// GitHub Releases page URL (for manual download links)
fn releases_page_url() -> String {
    format!(
        "https://github.com/{}/{}/releases",
        GITHUB_REPO_OWNER, GITHUB_REPO_NAME
    )
}

/// Get all candidate install paths (primary NSIS path first, then alternatives)
fn candidate_install_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();

    // Primary: NSIS currentUser → %LOCALAPPDATA%\{productName}\{productName}.exe
    if let Some(local) = dirs::data_local_dir() {
        paths.push(local.join(FI_MONITOR_PRODUCT_NAME).join(exe_name()));
    }

    // Fallback: Program Files
    if let Ok(pf) = std::env::var("ProgramFiles") {
        paths.push(PathBuf::from(&pf).join(FI_MONITOR_PRODUCT_NAME).join(exe_name()));
    }

    // Fallback: Program Files (x86)
    if let Ok(pf86) = std::env::var("ProgramFiles(x86)") {
        paths.push(PathBuf::from(&pf86).join(FI_MONITOR_PRODUCT_NAME).join(exe_name()));
    }

    paths
}

/// Find the first existing install path, or None
fn find_installed_path() -> Option<PathBuf> {
    candidate_install_paths().into_iter().find(|p| p.exists())
}

/// Check if FI Monitor is installed
#[tauri::command]
pub fn check_fi_monitor_installed() -> FiMonitorStatus {
    match find_installed_path() {
        Some(path) => FiMonitorStatus {
            installed: true,
            running: is_fi_monitor_running(),
            version: read_fi_monitor_version(&path),
            install_path: Some(path.to_string_lossy().to_string()),
        },
        None => FiMonitorStatus {
            installed: false,
            running: false,
            version: None,
            install_path: None,
        },
    }
}

/// Read FI Monitor version from the NSIS uninstall registry key.
/// Returns None if the version cannot be determined.
fn read_fi_monitor_version(_exe_path: &PathBuf) -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        let reg_key = format!(
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{}",
            FI_MONITOR_PRODUCT_NAME
        );
        let output = Command::new("reg")
            .args(["query", &reg_key, "/v", "DisplayVersion"])
            .output()
            .ok()?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            // Output format: "    DisplayVersion    REG_SZ    1.0.0"
            for line in stdout.lines() {
                if line.contains("DisplayVersion") {
                    return line.split_whitespace().last().map(|s| s.to_string());
                }
            }
        }
        None
    }

    #[cfg(not(target_os = "windows"))]
    {
        None
    }
}

/// Check if FI Monitor process is currently running
fn is_fi_monitor_running() -> bool {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        let exe = exe_name();
        let filter = format!("IMAGENAME eq {}", exe);
        let output = Command::new("tasklist")
            .args(["/FI", &filter, "/FO", "CSV", "/NH"])
            .output();

        if let Ok(output) = output {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout.contains(&exe);
        }
    }
    false
}

/// Launch FI Monitor if installed
#[tauri::command]
pub fn launch_fi_monitor() -> Result<bool, MonitorError> {
    let status = check_fi_monitor_installed();

    if !status.installed {
        return Err(MonitorError::NotInstalled("FI Monitor is not installed".into()));
    }

    if status.running {
        return Ok(true); // Already running
    }

    if let Some(_path) = status.install_path {
        #[cfg(target_os = "windows")]
        {
            use std::process::Command;
            Command::new(&_path)
                .spawn()
                .map_err(|e| MonitorError::Io(format!("Failed to launch FI Monitor: {}", e)))?;
            return Ok(true);
        }
    }

    Err(MonitorError::NotInstalled("Could not find FI Monitor executable".into()))
}

/// Download FI Monitor installer from GitHub Releases
#[tauri::command]
pub async fn download_fi_monitor(app: tauri::AppHandle) -> Result<String, MonitorError> {
    use tauri::Emitter;

    let filename = installer_filename();
    let download_url = release_download_url();

    // Download to temp directory
    let temp_dir = std::env::temp_dir();
    let installer_path = temp_dir.join(&filename);

    let client = reqwest::Client::builder()
        .timeout(DOWNLOAD_TIMEOUT)
        .build()
        .map_err(|e| MonitorError::DownloadFailed(format!("Error al crear cliente HTTP: {}", e)))?;

    info!("Downloading FI Monitor from: {}", download_url);

    let response = client
        .get(&download_url)
        .send()
        .await
        .map_err(|e| classify_network_error(&e))?;

    if !response.status().is_success() {
        return Err(classify_http_status(response.status()));
    }

    let total_size = response.content_length().unwrap_or(0);
    let mut downloaded: u64 = 0;

    // Create file
    let mut file = tokio::fs::File::create(&installer_path)
        .await
        .map_err(|e| MonitorError::Io(format!("Failed to create installer file: {}", e)))?;

    // Stream download with progress updates
    use tokio::io::AsyncWriteExt;
    let mut stream = response.bytes_stream();
    use futures_util::StreamExt;

    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| MonitorError::DownloadFailed(format!("Download error: {}", e)))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| MonitorError::Io(format!("Write error: {}", e)))?;

        downloaded += chunk.len() as u64;

        let progress = DownloadProgress {
            downloaded_bytes: downloaded,
            total_bytes: total_size,
            percentage: if total_size > 0 {
                (downloaded as f32 / total_size as f32) * 100.0
            } else {
                0.0
            },
        };

        let _ = app.emit("fi-monitor-download-progress", progress);
    }

    file.flush()
        .await
        .map_err(|e| MonitorError::Io(format!("Flush error: {}", e)))?;

    Ok(installer_path.to_string_lossy().to_string())
}

/// Install FI Monitor silently from downloaded installer
#[tauri::command]
pub async fn install_fi_monitor_silent(_installer_path: String) -> Result<bool, MonitorError> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        // Run NSIS installer in silent mode
        let output = Command::new(&_installer_path)
            .args(["/S"]) // Silent install flag for NSIS
            .output()
            .map_err(|e| MonitorError::InstallFailed(format!("Failed to run installer: {}", e)))?;

        if output.status.success() {
            // Give it a moment to complete installation
            tokio::time::sleep(POST_INSTALL_DELAY).await;

            // Verify installation
            let status = check_fi_monitor_installed();
            if status.installed {
                return Ok(true);
            }
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        let exit_code = output.status.code().unwrap_or(-1);
        return Err(classify_install_error(&stderr, exit_code, &_installer_path));
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(MonitorError::NotInstalled("FI Monitor is only available for Windows".into()))
    }
}

/// Full install flow: download and install FI Monitor
#[tauri::command]
pub async fn install_fi_monitor_full(app: tauri::AppHandle) -> Result<bool, MonitorError> {
    use tauri::Emitter;

    info!("Starting full installation...");

    // Step 1: Download
    let _ = app.emit("fi-monitor-install-status", "Descargando FI Monitor...");
    info!("Step 1: Downloading installer...");
    let installer_path = match download_fi_monitor(app.clone()).await {
        Ok(path) => {
            info!("Downloaded to: {}", path);
            path
        }
        Err(e) => {
            warn!("Download failed: {}", e);
            return Err(MonitorError::DownloadFailed(format!("Download failed: {}", e)));
        }
    };

    // Step 2: Install
    let _ = app.emit("fi-monitor-install-status", "Instalando FI Monitor...");
    info!("Step 2: Running installer...");
    let result = match install_fi_monitor_silent(installer_path.clone()).await {
        Ok(success) => {
            info!("Install result: {}", success);
            success
        }
        Err(e) => {
            warn!("Install failed: {}", e);
            return Err(MonitorError::InstallFailed(format!("Install failed: {}", e)));
        }
    };

    // Step 3: Cleanup temp file
    info!("Step 3: Cleaning up temp file...");
    if let Err(e) = std::fs::remove_file(&installer_path) {
        warn!("Failed to cleanup temp installer: {}", e);
    }

    // Step 4: Launch if installed
    if result {
        let _ = app.emit("fi-monitor-install-status", "Iniciando FI Monitor...");
        info!("Step 4: Launching FI Monitor...");
        let _ = launch_fi_monitor();
    }

    info!("Installation complete!");
    Ok(result)
}

// =============================================================================
// ERROR CLASSIFICATION (DRY helpers)
// =============================================================================

/// Classify a reqwest network-level error into a user-friendly MonitorError
fn classify_network_error(e: &reqwest::Error) -> MonitorError {
    let msg = e.to_string().to_lowercase();
    let detail = if msg.contains("dns") || msg.contains("resolve") || msg.contains("name") {
        format!("No se pudo conectar al servidor de descargas. Verifica tu conexión a internet. ({})", e)
    } else if msg.contains("timeout") {
        format!("La conexión tardó demasiado. Verifica tu conexión a internet e intenta de nuevo. ({})", e)
    } else if msg.contains("ssl") || msg.contains("tls") || msg.contains("certificate") {
        format!("Error de conexión segura. Tu red o proxy puede estar bloqueando la descarga. ({})", e)
    } else {
        format!("Error de conexión al descargar FI Monitor: {}. Verifica tu internet y vuelve a intentar.", e)
    };
    MonitorError::DownloadFailed(detail)
}

/// Classify an HTTP status code into a user-friendly MonitorError
fn classify_http_status(status: reqwest::StatusCode) -> MonitorError {
    let detail = match status.as_u16() {
        404 => format!(
            "El instalador de FI Monitor v{} no se encontró en el servidor. \
             Es posible que esta versión aún no esté publicada. \
             Descárgalo manualmente desde {}",
            FI_MONITOR_VERSION, releases_page_url()
        ),
        403 => "Acceso denegado al servidor de descargas. Si usas VPN o proxy corporativo, \
               intenta desactivarlo temporalmente.".to_string(),
        _ => format!(
            "La descarga falló (HTTP {}). Intenta de nuevo o descarga manualmente desde {}",
            status, releases_page_url()
        ),
    };
    MonitorError::DownloadFailed(detail)
}

/// Classify an NSIS installer exit into a user-friendly MonitorError
fn classify_install_error(stderr: &str, exit_code: i32, installer_path: &str) -> MonitorError {
    let lower = stderr.to_lowercase();
    let is_permission_error = lower.contains("permission")
        || lower.contains("access")
        || exit_code == NSIS_EXIT_ACCESS_DENIED;

    let detail = if is_permission_error {
        format!(
            "Error de permisos durante la instalación. Tu antivirus o configuración de Windows \
             puede estar bloqueando la instalación. Intenta: 1) Desactivar temporalmente el \
             antivirus, 2) Ejecutar la instalación manual desde: {} (código: {})",
            installer_path, exit_code
        )
    } else {
        format!(
            "La instalación no se completó correctamente (código: {}). \
             Intenta la instalación manual ejecutando el archivo: {}",
            exit_code, installer_path
        )
    };
    MonitorError::InstallFailed(detail)
}
