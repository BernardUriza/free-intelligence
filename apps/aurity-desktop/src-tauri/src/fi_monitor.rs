// FI Monitor Integration Module
//
// Handles detection, download, installation, and launching of FI Monitor
// for cloud connectivity and tunnel management.

use serde::Serialize;
use std::path::PathBuf;
use std::process::Command;

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

/// Get the expected installation path for FI Monitor
fn get_fi_monitor_install_path() -> Option<PathBuf> {
    // Standard NSIS installation path
    let local_app_data = dirs::data_local_dir()?;
    Some(local_app_data.join("FI Monitor").join("FI Monitor.exe"))
}

/// Get alternative paths where FI Monitor might be installed
fn get_alternative_paths() -> Vec<PathBuf> {
    let mut paths = vec![];

    // User's program files (NSIS default)
    if let Some(local) = dirs::data_local_dir() {
        paths.push(local.join("FI Monitor").join("FI Monitor.exe"));
    }

    // Check Program Files
    if let Ok(pf) = std::env::var("ProgramFiles") {
        paths.push(PathBuf::from(&pf).join("FI Monitor").join("FI Monitor.exe"));
    }

    // Check Program Files (x86)
    if let Ok(pf86) = std::env::var("ProgramFiles(x86)") {
        paths.push(
            PathBuf::from(&pf86)
                .join("FI Monitor")
                .join("FI Monitor.exe"),
        );
    }

    paths
}

/// Check if FI Monitor is installed
#[tauri::command]
pub fn check_fi_monitor_installed() -> FiMonitorStatus {
    // Check standard path first
    if let Some(path) = get_fi_monitor_install_path() {
        if path.exists() {
            return FiMonitorStatus {
                installed: true,
                running: is_fi_monitor_running(),
                version: Some("1.0.0".to_string()), // TODO: read from registry/manifest
                install_path: Some(path.to_string_lossy().to_string()),
            };
        }
    }

    // Check alternative paths
    for path in get_alternative_paths() {
        if path.exists() {
            return FiMonitorStatus {
                installed: true,
                running: is_fi_monitor_running(),
                version: Some("1.0.0".to_string()),
                install_path: Some(path.to_string_lossy().to_string()),
            };
        }
    }

    FiMonitorStatus {
        installed: false,
        running: false,
        version: None,
        install_path: None,
    }
}

/// Check if FI Monitor process is currently running
fn is_fi_monitor_running() -> bool {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("tasklist")
            .args(["/FI", "IMAGENAME eq FI Monitor.exe", "/FO", "CSV", "/NH"])
            .output();

        if let Ok(output) = output {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout.contains("FI Monitor.exe");
        }
    }
    false
}

/// Launch FI Monitor if installed
#[tauri::command]
pub fn launch_fi_monitor() -> Result<bool, String> {
    let status = check_fi_monitor_installed();

    if !status.installed {
        return Err("FI Monitor is not installed".to_string());
    }

    if status.running {
        return Ok(true); // Already running
    }

    if let Some(path) = status.install_path {
        #[cfg(target_os = "windows")]
        {
            Command::new(&path)
                .spawn()
                .map_err(|e| format!("Failed to launch FI Monitor: {}", e))?;
            return Ok(true);
        }
    }

    Err("Could not find FI Monitor executable".to_string())
}

/// Download FI Monitor installer from Azure blob storage
#[tauri::command]
pub async fn download_fi_monitor(app: tauri::AppHandle) -> Result<String, String> {
    use tauri::Emitter;

    // Azure blob URL for FI Monitor installer
    let download_url = "https://aurityreleases.blob.core.windows.net/releases/fi-monitor/FI%20Monitor_1.0.0_x64-setup.exe";

    // Download to temp directory
    let temp_dir = std::env::temp_dir();
    let installer_path = temp_dir.join("FI Monitor_setup.exe");

    // Download with progress
    let client = reqwest::Client::new();
    let response = client
        .get(download_url)
        .send()
        .await
        .map_err(|e| format!("Failed to start download: {}", e))?;

    if !response.status().is_success() {
        return Err(format!(
            "Download failed with status: {}",
            response.status()
        ));
    }

    let total_size = response.content_length().unwrap_or(0);
    let mut downloaded: u64 = 0;

    // Create file
    let mut file = tokio::fs::File::create(&installer_path)
        .await
        .map_err(|e| format!("Failed to create installer file: {}", e))?;

    // Stream download with progress updates
    use tokio::io::AsyncWriteExt;
    let mut stream = response.bytes_stream();
    use futures_util::StreamExt;

    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| format!("Download error: {}", e))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("Write error: {}", e))?;

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
        .map_err(|e| format!("Flush error: {}", e))?;

    Ok(installer_path.to_string_lossy().to_string())
}

/// Install FI Monitor silently from downloaded installer
#[tauri::command]
pub async fn install_fi_monitor_silent(installer_path: String) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        // Run NSIS installer in silent mode
        let output = Command::new(&installer_path)
            .args(["/S"]) // Silent install flag for NSIS
            .output()
            .map_err(|e| format!("Failed to run installer: {}", e))?;

        if output.status.success() {
            // Give it a moment to complete installation
            tokio::time::sleep(std::time::Duration::from_secs(2)).await;

            // Verify installation
            let status = check_fi_monitor_installed();
            if status.installed {
                return Ok(true);
            }
        }

        return Err("Installation may have failed. Please try manual installation.".to_string());
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("FI Monitor is only available for Windows".to_string())
    }
}

/// Full install flow: download and install FI Monitor
#[tauri::command]
pub async fn install_fi_monitor_full(app: tauri::AppHandle) -> Result<bool, String> {
    use tauri::Emitter;

    println!("[FI Monitor] Starting full installation...");

    // Step 1: Download
    let _ = app.emit("fi-monitor-install-status", "Descargando FI Monitor...");
    println!("[FI Monitor] Step 1: Downloading installer...");
    let installer_path = match download_fi_monitor(app.clone()).await {
        Ok(path) => {
            println!("[FI Monitor] Downloaded to: {}", path);
            path
        }
        Err(e) => {
            println!("[FI Monitor] Download failed: {}", e);
            return Err(format!("Download failed: {}", e));
        }
    };

    // Step 2: Install
    let _ = app.emit("fi-monitor-install-status", "Instalando FI Monitor...");
    println!("[FI Monitor] Step 2: Running installer...");
    let result = match install_fi_monitor_silent(installer_path.clone()).await {
        Ok(success) => {
            println!("[FI Monitor] Install result: {}", success);
            success
        }
        Err(e) => {
            println!("[FI Monitor] Install failed: {}", e);
            return Err(format!("Install failed: {}", e));
        }
    };

    // Step 3: Cleanup temp file
    println!("[FI Monitor] Step 3: Cleaning up temp file...");
    let _ = std::fs::remove_file(&installer_path);

    // Step 4: Launch if installed
    if result {
        let _ = app.emit("fi-monitor-install-status", "Iniciando FI Monitor...");
        println!("[FI Monitor] Step 4: Launching FI Monitor...");
        let _ = launch_fi_monitor();
    }

    println!("[FI Monitor] Installation complete!");
    Ok(result)
}
