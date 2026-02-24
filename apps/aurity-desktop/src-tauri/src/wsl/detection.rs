// WSL Detection — queries whether WSL is installed, which distro, and version.

use super::{WslError, WslStatus};

#[cfg(target_os = "windows")]
use std::process::Command;

/// Check if WSL is installed and get status
#[tauri::command]
pub fn check_wsl_status() -> Result<WslStatus, WslError> {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("wsl").args(["--status"]).output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    Ok(build_installed_status())
                } else {
                    let stderr = String::from_utf8_lossy(&result.stderr);
                    if stderr.contains("no installed distributions")
                        || stderr.contains("not installed")
                    {
                        Ok(WslStatus {
                            installed: false,
                            distro: None,
                            version: None,
                            backend_installed: false,
                            backend_running: false,
                        })
                    } else {
                        // WSL exists but returned a non-zero exit code for other reasons
                        Ok(build_installed_status())
                    }
                }
            }
            Err(_) => {
                // wsl.exe not found at all
                Ok(WslStatus {
                    installed: false,
                    distro: None,
                    version: None,
                    backend_installed: false,
                    backend_running: false,
                })
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

// ---------------------------------------------------------------------------
// Internal helpers (Windows only)
// ---------------------------------------------------------------------------

/// Build a full WslStatus for an installed WSL.
#[cfg(target_os = "windows")]
fn build_installed_status() -> WslStatus {
    use super::backend::{check_backend_installed, check_backend_running};

    WslStatus {
        installed: true,
        distro: get_default_distro(),
        version: get_wsl_version(),
        backend_installed: check_backend_installed(),
        backend_running: check_backend_running(),
    }
}

/// Get the default WSL distro name.
#[cfg(target_os = "windows")]
fn get_default_distro() -> Option<String> {
    let output = Command::new("wsl")
        .args(["--list", "--quiet"])
        .output()
        .ok()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        // First line is the default distro (removing BOM and whitespace)
        stdout
            .lines()
            .next()
            .map(|s| s.trim().trim_start_matches('\u{feff}').to_string())
            .filter(|s| !s.is_empty())
    } else {
        None
    }
}

/// Get WSL version (1 or 2).
#[cfg(target_os = "windows")]
fn get_wsl_version() -> Option<u32> {
    let output = Command::new("wsl").args(["--version"]).output().ok()?;

    if output.status.success() {
        // If --version succeeds, WSL 2 is available
        Some(2)
    } else {
        // Fallback — assume WSL 1
        Some(1)
    }
}
