// Install — silent install from bundle or download from ollama.com.

use std::process::Command;

use super::detection::check_ollama_installed;

/// Get path to bundled Ollama installer (Windows only).
#[cfg(target_os = "windows")]
fn get_bundled_installer_path() -> Option<std::path::PathBuf> {
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

/// Run the Ollama Inno Setup installer silently and verify installation.
#[cfg(target_os = "windows")]
async fn run_installer_and_verify(
    installer_path: &std::path::Path,
    app: &tauri::AppHandle,
) -> Result<bool, String> {
    use tauri::Emitter;

    let _ = app.emit("ollama-install-status", "Instalando Ollama...");

    let output = Command::new(installer_path)
        .args(["/SILENT", "/NORESTART"])
        .output()
        .map_err(|e| format!("Failed to run installer: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Installer failed: {}", stderr));
    }

    println!("[FI Monitor] Ollama installed successfully");
    let _ = app.emit("ollama-install-status", "Ollama instalado ✓");

    // Wait for installation to settle
    tokio::time::sleep(std::time::Duration::from_secs(3)).await;

    // Verify installation
    let status = check_ollama_installed();
    if status.installed {
        Ok(true)
    } else {
        Err("Installation completed but Ollama not detected".to_string())
    }
}

/// Install Ollama silently from the bundled installer (Windows only).
#[tauri::command]
pub async fn install_ollama_silent(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit(
            "ollama-install-status",
            "Buscando instalador bundleado...",
        );

        let installer_path = get_bundled_installer_path()
            .ok_or("Ollama installer not found in bundle".to_string())?;

        println!(
            "[FI Monitor] Found bundled Ollama installer: {:?}",
            installer_path
        );

        return run_installer_and_verify(&installer_path, &_app).await;
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}

/// Download Ollama from ollama.com and install silently (fallback when not bundled).
#[tauri::command]
pub async fn download_and_install_ollama(_app: tauri::AppHandle) -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;
        let _ = _app.emit("ollama-install-status", "Descargando Ollama...");

        let download_url = "https://ollama.com/download/OllamaSetup.exe";
        let installer_path = std::env::temp_dir().join("OllamaSetup.exe");

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

        // Run installer and verify
        let result = run_installer_and_verify(&installer_path, &_app).await;

        // Cleanup temp file
        if let Err(e) = std::fs::remove_file(&installer_path) {
            eprintln!(
                "[FI Monitor] Failed to cleanup temp installer {:?}: {}",
                installer_path, e
            );
        }

        return result;
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Auto-installation is only supported on Windows".to_string())
    }
}
