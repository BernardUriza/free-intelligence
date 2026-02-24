// Autostart — Windows registry Run key management.

use log::info;

use crate::errors::AppError;

#[cfg(target_os = "windows")]
const AUTOSTART_KEY: &str = "AurityDesktop";

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/// Internal function to setup Windows autostart
#[cfg(target_os = "windows")]
fn setup_windows_autostart_internal() -> Result<bool, AppError> {
    use std::process::Command;

    let exe_path = std::env::current_exe()
        .map_err(|e| AppError::Io(format!("Failed to get exe path: {}", e)))?;

    // Add to HKCU\Software\Microsoft\Windows\CurrentVersion\Run
    let output = Command::new("reg")
        .args([
            "add",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "/v",
            AUTOSTART_KEY,
            "/t",
            "REG_SZ",
            "/d",
            &exe_path.to_string_lossy(),
            "/f", // Force overwrite
        ])
        .output()
        .map_err(|e| AppError::Script(format!("Failed to execute reg: {}", e)))?;

    if output.status.success() {
        Ok(true)
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(AppError::Script(format!(
            "Failed to add registry key: {}",
            stderr
        )))
    }
}

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Setup Windows autostart (adds to registry Run key)
#[tauri::command]
pub fn setup_windows_autostart() -> Result<bool, AppError> {
    #[cfg(target_os = "windows")]
    {
        let result = setup_windows_autostart_internal();
        if result.is_ok() {
            info!("Windows autostart enabled");
        }
        result
    }

    #[cfg(not(target_os = "windows"))]
    {
        Ok(false) // Not applicable on other platforms
    }
}

/// Remove Windows autostart
#[tauri::command]
pub fn remove_windows_autostart() -> Result<bool, AppError> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;

        let output = Command::new("reg")
            .args([
                "delete",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
                "/v",
                AUTOSTART_KEY,
                "/f",
            ])
            .output()
            .map_err(|e| AppError::Script(format!("Failed to execute reg: {}", e)))?;

        if output.status.success() {
            info!("Windows autostart disabled");
            Ok(true)
        } else {
            // Key might not exist, that's ok
            Ok(false)
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Ok(false)
    }
}

/// Check if Windows autostart is enabled
#[tauri::command]
pub fn check_windows_autostart() -> Result<bool, AppError> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;

        let output = Command::new("reg")
            .args([
                "query",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
                "/v",
                AUTOSTART_KEY,
            ])
            .output()
            .map_err(|e| AppError::Script(format!("Failed to execute reg: {}", e)))?;

        Ok(output.status.success())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Ok(false)
    }
}
