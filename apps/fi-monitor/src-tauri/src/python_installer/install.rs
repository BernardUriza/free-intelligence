// Python installation — bundled silent install and download-from-web fallback.

use std::process::Command;

use super::detection::check_python_installed;

/// Silent install args shared by both bundled and downloaded installers.
const INSTALLER_ARGS: &[&str] = &[
    "/quiet",
    "InstallAllUsers=0",
    "PrependPath=1",
    "Include_pip=1",
    "Include_test=0",
];

/// Install Python 3.14 silently from the bundled installer (Windows only).
#[tauri::command]
pub(crate) async fn install_python_silent(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use std::path::PathBuf;
        use tauri::Emitter;

        let _ = _app.emit("python-install-status", "Buscando instalador de Python...");

        let installer_path = get_bundled_installer_path()
            .ok_or_else(|| "Python installer not found in bundle".to_string())?;

        println!(
            "[FI Monitor] Found bundled Python installer: {:?}",
            installer_path
        );
        let _ = _app.emit("python-install-status", "Instalando Python 3.14...");

        run_installer_and_verify(&_app, &installer_path).await
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}

/// Download Python from python.org and install (Windows fallback).
#[tauri::command]
pub(crate) async fn download_and_install_python(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;

        let _ = _app.emit(
            "python-install-status",
            "Descargando Python desde python.org...",
        );

        let installer_path = download_installer().await?;

        let _ = _app.emit("python-install-status", "Instalando Python...");

        let result = run_installer_and_verify(&_app, &installer_path).await;

        // Clean up temp file regardless of result
        if let Err(e) = std::fs::remove_file(&installer_path) {
            eprintln!(
                "[FI Monitor] Failed to cleanup temp installer {:?}: {}",
                installer_path, e
            );
        }

        result
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}

// ---------------------------------------------------------------------------
// Helpers (Windows-only implementations)
// ---------------------------------------------------------------------------

/// Run the Python installer with standard args, wait, and verify installation.
#[cfg(target_os = "windows")]
async fn run_installer_and_verify(
    app: &tauri::AppHandle,
    installer_path: &std::path::Path,
) -> Result<bool, String> {
    use tauri::Emitter;

    let output = Command::new(installer_path)
        .args(INSTALLER_ARGS)
        .output()
        .map_err(|e| format!("Failed to run Python installer: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python installer failed: {}", stderr));
    }

    println!("[FI Monitor] Python installed successfully");
    let _ = app.emit("python-install-status", "Python 3.14 instalado ✓");

    // Give the installer time to finalise
    tokio::time::sleep(std::time::Duration::from_secs(5)).await;

    let status = check_python_installed();
    if status.installed {
        Ok(true)
    } else {
        Err("Installation completed but Python not detected".to_string())
    }
}

/// Locate the bundled Python installer next to the running executable.
#[cfg(target_os = "windows")]
fn get_bundled_installer_path() -> Option<std::path::PathBuf> {
    let exe_dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    let installer_path = exe_dir.join("python-3.14.0-amd64.exe");
    installer_path.exists().then_some(installer_path)
}

/// Download the Python installer from python.org to a temp directory.
#[cfg(target_os = "windows")]
async fn download_installer() -> Result<std::path::PathBuf, String> {
    let url = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe";
    let installer_path = std::env::temp_dir().join("python-3.14.0-amd64.exe");

    println!("[FI Monitor] Downloading Python from: {}", url);

    let response = reqwest::get(url)
        .await
        .map_err(|e| format!("Download failed: {}", e))?;

    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    std::fs::write(&installer_path, bytes)
        .map_err(|e| format!("Failed to write installer: {}", e))?;

    println!(
        "[FI Monitor] Python installer downloaded to {:?}",
        installer_path
    );

    Ok(installer_path)
}
