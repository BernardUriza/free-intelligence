// Detection — check installed status, running process, registry version.

use super::paths::{exe_name, find_installed_path};
use super::{FiMonitorStatus, FI_MONITOR_PRODUCT_NAME};

/// Check if FI Monitor is installed.
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

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Read FI Monitor version from the NSIS uninstall registry key.
/// Returns `None` if the version cannot be determined.
fn read_fi_monitor_version(_exe_path: &std::path::PathBuf) -> Option<String> {
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

/// Check if FI Monitor process is currently running.
pub(crate) fn is_fi_monitor_running() -> bool {
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
