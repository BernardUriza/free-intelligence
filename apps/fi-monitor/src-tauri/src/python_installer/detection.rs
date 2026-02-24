// Python detection — version check and path discovery.

#[cfg(target_os = "windows")]
use std::path::PathBuf;
use std::process::Command;

use super::PythonInstallStatus;

/// Check if Python 3.14+ is installed on the system.
#[tauri::command]
pub(crate) fn check_python_installed() -> PythonInstallStatus {
    let python_cmd = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    match Command::new(python_cmd).arg("--version").output() {
        Ok(output) if output.status.success() => {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();

            if is_python_314_or_higher(&version) {
                PythonInstallStatus {
                    installed: true,
                    version: Some(version),
                    install_path: find_python_path(),
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

/// Check if the version string represents Python 3.14 or higher.
fn is_python_314_or_higher(version_str: &str) -> bool {
    // Parse "Python 3.14.0" -> (3, 14)
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

/// Find the Python executable path on the system.
fn find_python_path() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        let mut paths = vec![
            PathBuf::from(r"C:\Program Files\Python314\python.exe"),
            PathBuf::from(r"C:\Program Files (x86)\Python314\python.exe"),
        ];

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
        if let Ok(output) = Command::new("which").arg("python3").output() {
            if output.status.success() {
                return Some(String::from_utf8_lossy(&output.stdout).trim().to_string());
            }
        }
    }

    None
}
