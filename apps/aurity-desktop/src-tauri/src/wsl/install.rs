// WSL Installation — install WSL distro and enable Windows features.

use super::WslError;

#[cfg(target_os = "windows")]
use std::process::Command;

/// Install WSL with Ubuntu (requires elevation).
/// Uses PowerShell `Start-Process -Verb RunAs` to trigger UAC prompt.
#[tauri::command]
pub fn install_wsl() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("powershell")
            .args([
                "-Command",
                "Start-Process",
                "wsl",
                "-ArgumentList",
                "'--install', '-d', 'Ubuntu'",
                "-Verb",
                "RunAs",
                "-Wait",
            ])
            .output()
            .map_err(|e| {
                WslError::CommandFailed(format!(
                    "No se pudo iniciar la instalación de WSL: {}",
                    e
                ))
            })?;

        if output.status.success() {
            Ok("Instalación de WSL iniciada. Es posible que se requiera reiniciar el equipo."
                .to_string())
        } else {
            Err(classify_install_error(&output.stderr))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL installation is only available on Windows".into(),
        ))
    }
}

/// Enable WSL feature via DISM (pre-Windows 11 method).
#[tauri::command]
pub fn enable_wsl_feature() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let script = r#"
            $result = @{success=$true; message=""}
            try {
                $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
                $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform

                if ($wslFeature.State -eq "Enabled" -and $vmFeature.State -eq "Enabled") {
                    $result.message = "WSL features already enabled"
                } else {
                    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
                    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
                    $result.message = "WSL features enabled. Restart required."
                }
            } catch {
                $result.success = $false
                $result.message = $_.Exception.Message
            }
            $result | ConvertTo-Json
        "#;

        let output = Command::new("powershell")
            .args(["-ExecutionPolicy", "Bypass", "-Command", script])
            .output()
            .map_err(|e| {
                WslError::CommandFailed(format!("Failed to enable WSL feature: {}", e))
            })?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        Ok(stdout.to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

// ---------------------------------------------------------------------------
// Error classification
// ---------------------------------------------------------------------------

/// Classify a WSL install failure into a user-friendly Spanish error.
#[cfg(target_os = "windows")]
fn classify_install_error(stderr_bytes: &[u8]) -> WslError {
    let stderr = String::from_utf8_lossy(stderr_bytes);
    let lower = stderr.to_lowercase();

    if lower.contains("cancelled") || lower.contains("canceled") || lower.contains("user") {
        WslError::CommandFailed(
            "La instalación de WSL requiere permisos de administrador. \
             Se mostró una ventana de autorización que fue cancelada o denegada. \
             Haz clic en 'Sí' cuando Windows te pida permiso."
                .to_string(),
        )
    } else if lower.contains("access") || lower.contains("denied") || lower.contains("permission")
    {
        WslError::CommandFailed(
            "No se tienen permisos suficientes para instalar WSL. \
             Esta operación requiere ejecutarse como administrador. \
             Si estás en una PC corporativa, contacta a tu equipo de TI."
                .to_string(),
        )
    } else {
        WslError::CommandFailed(format!(
            "La instalación de WSL falló: {}. \
             Intenta ejecutar 'wsl --install' manualmente desde PowerShell como administrador.",
            stderr
        ))
    }
}
