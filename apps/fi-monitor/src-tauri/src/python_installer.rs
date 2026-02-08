// Python 3.14 Installation Module for FI Monitor
//
// Handles automatic installation of Python 3.14 if bundled with the installer.
// On Windows, python-3.14.0-amd64.exe is bundled in src-tauri/binaries/ and installed
// silently when FI Monitor detects Python is not available.

use serde::Serialize;
#[cfg(target_os = "windows")]
use std::path::PathBuf;
use std::process::Command;

#[derive(Serialize)]
pub struct PythonInstallStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub install_path: Option<String>,
}

/// Check if Python 3.14+ is installed on the system
#[tauri::command]
pub fn check_python_installed() -> PythonInstallStatus {
    // Try running `python --version`
    let python_cmd = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    match Command::new(python_cmd).arg("--version").output() {
        Ok(output) if output.status.success() => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            let version = version_str.trim().to_string();

            // Check if version is 3.14+
            if is_python_314_or_higher(&version) {
                let install_path = find_python_path();
                PythonInstallStatus {
                    installed: true,
                    version: Some(version),
                    install_path,
                }
            } else {
                PythonInstallStatus {
                    installed: false,
                    version: Some(version),
                    install_path: None,
                }
            }
        }
        _ => PythonInstallStatus {
            installed: false,
            version: None,
            install_path: None,
        },
    }
}

/// Check if Python version is 3.14 or higher
fn is_python_314_or_higher(version_str: &str) -> bool {
    // Parse "Python 3.14.0" -> (3, 14, 0)
    if let Some(version_part) = version_str.split_whitespace().nth(1) {
        let parts: Vec<&str> = version_part.split('.').collect();
        if parts.len() >= 2 {
            if let (Ok(major), Ok(minor)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
                return major > 3 || (major == 3 && minor >= 14);
            }
        }
    }
    false
}

/// Find Python executable path
fn find_python_path() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        // Common Windows paths
        let mut paths = vec![
            PathBuf::from(r"C:\Program Files\Python314\python.exe"),
            PathBuf::from(r"C:\Program Files (x86)\Python314\python.exe"),
        ];

        // Also check user's local AppData
        if let Some(local_app_data) = dirs::data_local_dir() {
            paths.push(
                local_app_data
                    .join("Programs")
                    .join("Python")
                    .join("Python314")
                    .join("python.exe"),
            );
        }

        for path in paths {
            if path.exists() {
                return Some(path.to_string_lossy().to_string());
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        // On Unix, check standard paths
        if let Ok(output) = Command::new("which").arg("python3").output() {
            if output.status.success() {
                return Some(String::from_utf8_lossy(&output.stdout).trim().to_string());
            }
        }
    }

    None
}

/// Get path to bundled Python installer (Windows only)
#[cfg(target_os = "windows")]
fn get_bundled_python_installer_path() -> Option<PathBuf> {
    // When bundled, python-3.14.0-amd64.exe is in the same directory as FI Monitor.exe
    let exe_dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    let installer_path = exe_dir.join("python-3.14.0-amd64.exe");
    installer_path.exists().then_some(installer_path)
}

/// Install Python 3.14 silently from bundled installer (Windows only)
#[tauri::command]
pub async fn install_python_silent(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit("python-install-status", "Buscando instalador de Python...");

        let installer_path = get_bundled_python_installer_path()
            .ok_or("Python installer not found in bundle".to_string())?;

        println!(
            "[FI Monitor] Found bundled Python installer: {:?}",
            installer_path
        );
        let _ = _app.emit("python-install-status", "Instalando Python 3.14...");

        // Run Python installer silently
        // Python installer supports /quiet for silent install
        // InstallAllUsers=0 -> per-user install (no admin required)
        // PrependPath=1 -> add to PATH
        let output = Command::new(&installer_path)
            .args([
                "/quiet",
                "InstallAllUsers=0",
                "PrependPath=1",
                "Include_pip=1",
                "Include_test=0",
            ])
            .output()
            .map_err(|e| format!("Failed to run Python installer: {}", e))?;

        if output.status.success() {
            println!("[FI Monitor] Python installed successfully");
            let _ = _app.emit("python-install-status", "Python 3.14 instalado ✓");

            // Wait for installation to complete
            tokio::time::sleep(std::time::Duration::from_secs(5)).await;

            // Verify installation
            let status = check_python_installed();
            if status.installed {
                return Ok(true);
            } else {
                return Err("Installation completed but Python not detected".to_string());
            }
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Python installer failed: {}", stderr));
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}

/// Download and install Python from python.org (fallback)
#[tauri::command]
pub async fn download_and_install_python(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit(
            "python-install-status",
            "Descargando Python desde python.org...",
        );

        let url = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe";
        let temp_dir = std::env::temp_dir();
        let installer_path = temp_dir.join("python-3.14.0-amd64.exe");

        println!("[FI Monitor] Downloading Python from: {}", url);

        // Download using reqwest
        let response = reqwest::get(url)
            .await
            .map_err(|e| format!("Download failed: {}", e))?;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        std::fs::write(&installer_path, bytes)
            .map_err(|e| format!("Failed to write installer: {}", e))?;

        println!("[FI Monitor] Python installer downloaded to {:?}", installer_path);
        let _ = _app.emit("python-install-status", "Instalando Python...");

        // Run installer
        let output = Command::new(&installer_path)
            .args([
                "/quiet",
                "InstallAllUsers=0",
                "PrependPath=1",
                "Include_pip=1",
                "Include_test=0",
            ])
            .output()
            .map_err(|e| format!("Failed to run installer: {}", e))?;

        // Clean up
        if let Err(e) = std::fs::remove_file(&installer_path) {
            eprintln!("[FI Monitor] Failed to cleanup temp installer {:?}: {}", installer_path, e);
        }

        if output.status.success() {
            let _ = _app.emit("python-install-status", "Python instalado ✓");
            tokio::time::sleep(std::time::Duration::from_secs(5)).await;

            let status = check_python_installed();
            Ok(status.installed)
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("Installer failed: {}", stderr))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}
