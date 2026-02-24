// Install — silent NSIS installation, full orchestration flow (download → install → launch).

use log::{info, warn};
use tauri::Emitter;
use tokio::time::timeout;

use super::detection::check_fi_monitor_installed;
use super::download::download_fi_monitor;
use super::errors;
use super::{MonitorError, INSTALL_TIMEOUT, POST_INSTALL_DELAY};

/// Install FI Monitor silently from a downloaded NSIS installer.
/// Uses tokio::process to avoid blocking the async runtime, with a 5-minute timeout.
#[tauri::command]
pub async fn install_fi_monitor_silent(_installer_path: String) -> Result<bool, MonitorError> {
    #[cfg(target_os = "windows")]
    {
        use tokio::process::Command;

        let output = timeout(
            INSTALL_TIMEOUT,
            Command::new(&_installer_path)
                .args(["/S"]) // NSIS silent install flag
                .output(),
        )
        .await
        .map_err(|_| {
            MonitorError::InstallFailed(
                "La instalación tardó demasiado (timeout 5 min). \
                 Intenta ejecutar el instalador manualmente."
                    .into(),
            )
        })?
        .map_err(|e| MonitorError::InstallFailed(format!("Failed to run installer: {}", e)))?;

        if output.status.success() {
            tokio::time::sleep(POST_INSTALL_DELAY).await;

            let status = check_fi_monitor_installed();
            if status.installed {
                return Ok(true);
            }
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        let exit_code = output.status.code().unwrap_or(-1);
        return Err(errors::classify_install_error(
            &stderr,
            exit_code,
            &_installer_path,
        ));
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(MonitorError::NotInstalled(
            "FI Monitor is only available for Windows".into(),
        ))
    }
}

/// Launch FI Monitor if installed.
#[tauri::command]
pub fn launch_fi_monitor() -> Result<bool, MonitorError> {
    let status = check_fi_monitor_installed();

    if !status.installed {
        return Err(MonitorError::NotInstalled(
            "FI Monitor is not installed".into(),
        ));
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

    Err(MonitorError::NotInstalled(
        "Could not find FI Monitor executable".into(),
    ))
}

/// Full install flow: download → install → cleanup → launch.
#[tauri::command]
pub async fn install_fi_monitor_full(app: tauri::AppHandle) -> Result<bool, MonitorError> {
    info!("Starting full installation...");

    // Step 1: Download
    let _ = app.emit("fi-monitor-install-status", "Descargando FI Monitor...");
    info!("Step 1: Downloading installer...");
    let installer_path = download_fi_monitor(app.clone())
        .await
        .map(|path| {
            info!("Downloaded to: {}", path);
            path
        })
        .map_err(|e| {
            warn!("Download failed: {}", e);
            MonitorError::DownloadFailed(format!("Download failed: {}", e))
        })?;

    // Step 2: Install
    let _ = app.emit("fi-monitor-install-status", "Instalando FI Monitor...");
    info!("Step 2: Running installer...");
    let result = install_fi_monitor_silent(installer_path.clone())
        .await
        .map(|success| {
            info!("Install result: {}", success);
            success
        })
        .map_err(|e| {
            warn!("Install failed: {}", e);
            MonitorError::InstallFailed(format!("Install failed: {}", e))
        })?;

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
