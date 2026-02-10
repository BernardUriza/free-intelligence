// Ollama Installation Module for FI Monitor
//
// Handles automatic installation of Ollama if bundled with the installer.
// On Windows, OllamaSetup.exe is bundled in src-tauri/binaries/ and installed
// silently when FI Monitor detects Ollama is not available.

use serde::Serialize;
#[cfg(target_os = "windows")]
use std::path::PathBuf;
use std::process::Command;

#[derive(Serialize)]
pub struct OllamaInstallStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub install_path: Option<String>,
}

/// Check if Ollama is installed on the system
#[tauri::command]
pub fn check_ollama_installed() -> OllamaInstallStatus {
    // Try running `ollama --version`
    match Command::new("ollama").arg("--version").output() {
        Ok(output) if output.status.success() => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            let version = version_str.trim().to_string();

            // Try to find install path
            let install_path = find_ollama_path();

            OllamaInstallStatus {
                installed: true,
                version: Some(version),
                install_path,
            }
        }
        _ => OllamaInstallStatus {
            installed: false,
            version: None,
            install_path: None,
        },
    }
}

/// Find Ollama executable path
fn find_ollama_path() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        // Common Windows paths
        let mut paths = vec![
            PathBuf::from(r"C:\Program Files\Ollama\ollama.exe"),
            PathBuf::from(r"C:\Program Files (x86)\Ollama\ollama.exe"),
        ];

        // Also check user's local AppData
        if let Some(local_app_data) = dirs::data_local_dir() {
            paths.push(
                local_app_data
                    .join("Programs")
                    .join("Ollama")
                    .join("ollama.exe"),
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
        if let Ok(output) = Command::new("which").arg("ollama").output() {
            if output.status.success() {
                return Some(String::from_utf8_lossy(&output.stdout).trim().to_string());
            }
        }
    }

    None
}

/// Get path to bundled Ollama installer (Windows only)
#[cfg(target_os = "windows")]
fn get_bundled_installer_path() -> Option<PathBuf> {
    // When bundled, OllamaSetup.exe is in the same directory as FI Monitor.exe
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let installer_path = exe_dir.join("OllamaSetup.exe");
            if installer_path.exists() {
                return Some(installer_path);
            }
        }
    }
    None
}

/// Install Ollama silently from bundled installer (Windows only)
#[tauri::command]
pub async fn install_ollama_silent(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit("ollama-install-status", "Buscando instalador bundleado...");

        let installer_path = get_bundled_installer_path()
            .ok_or("Ollama installer not found in bundle".to_string())?;

        println!(
            "[FI Monitor] Found bundled Ollama installer: {:?}",
            installer_path
        );
        let _ = _app.emit("ollama-install-status", "Instalando Ollama...");

        // Run Ollama installer silently
        // Ollama uses Inno Setup, which supports /SILENT flag
        let output = Command::new(&installer_path)
            .args(["/SILENT", "/NORESTART"])
            .output()
            .map_err(|e| format!("Failed to run installer: {}", e))?;

        if output.status.success() {
            println!("[FI Monitor] Ollama installed successfully");
            let _ = _app.emit("ollama-install-status", "Ollama instalado ✓");

            // Wait a moment for installation to complete
            tokio::time::sleep(std::time::Duration::from_secs(3)).await;

            // Verify installation
            let status = check_ollama_installed();
            if status.installed {
                return Ok(true);
            } else {
                return Err("Installation completed but Ollama not detected".to_string());
            }
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Installer failed: {}", stderr));
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}

/// Download and install Ollama from ollama.com (fallback if not bundled)
#[tauri::command]
pub async fn download_and_install_ollama(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit("ollama-install-status", "Descargando Ollama...");

        let download_url = "https://ollama.com/download/OllamaSetup.exe";
        let temp_dir = std::env::temp_dir();
        let installer_path = temp_dir.join("OllamaSetup.exe");

        // Download installer
        println!("[FI Monitor] Downloading Ollama from: {}", download_url);
        let client = reqwest::Client::new();
        let response = client
            .get(download_url)
            .send()
            .await
            .map_err(|e| format!("Download failed: {}", e))?;

        if !response.status().is_success() {
            return Err(format!(
                "Download failed with status: {}",
                response.status()
            ));
        }

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        tokio::fs::write(&installer_path, bytes)
            .await
            .map_err(|e| format!("Failed to save installer: {}", e))?;

        println!("[FI Monitor] Downloaded to: {:?}", installer_path);
        let _ = _app.emit("ollama-install-status", "Instalando Ollama...");

        // Run installer silently
        let output = Command::new(&installer_path)
            .args(["/SILENT", "/NORESTART"])
            .output()
            .map_err(|e| format!("Failed to run installer: {}", e))?;

        // Cleanup temp file
        if let Err(e) = std::fs::remove_file(&installer_path) {
            eprintln!("[FI Monitor] Failed to cleanup temp installer {:?}: {}", installer_path, e);
        }

        if output.status.success() {
            println!("[FI Monitor] Ollama installed successfully");
            let _ = _app.emit("ollama-install-status", "Ollama instalado ✓");

            // Wait for installation to complete
            tokio::time::sleep(std::time::Duration::from_secs(3)).await;

            // Verify installation
            let status = check_ollama_installed();
            if status.installed {
                return Ok(true);
            } else {
                return Err("Installation completed but Ollama not detected".to_string());
            }
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Installer failed: {}", stderr));
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}
