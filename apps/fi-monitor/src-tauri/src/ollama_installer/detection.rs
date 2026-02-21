// Detection — check if Ollama is installed and locate its executable.

#[cfg(target_os = "windows")]
use std::path::PathBuf;
use std::process::Command;

use super::OllamaInstallStatus;

/// Check if Ollama is installed on the system.
#[tauri::command]
pub fn check_ollama_installed() -> OllamaInstallStatus {
    match Command::new("ollama").arg("--version").output() {
        Ok(output) if output.status.success() => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            OllamaInstallStatus {
                installed: true,
                version: Some(version_str.trim().to_string()),
                install_path: find_ollama_path(),
            }
        }
        _ => OllamaInstallStatus {
            installed: false,
            version: None,
            install_path: None,
        },
    }
}

/// Find the Ollama executable path on the system.
pub(crate) fn find_ollama_path() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
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
        if let Ok(output) = Command::new("which").arg("ollama").output() {
            if output.status.success() {
                return Some(String::from_utf8_lossy(&output.stdout).trim().to_string());
            }
        }
    }

    None
}
