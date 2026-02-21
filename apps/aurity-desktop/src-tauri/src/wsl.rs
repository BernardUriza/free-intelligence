// WSL (Windows Subsystem for Linux) Integration
//
// This module provides commands to:
// 1. Check if WSL is installed
// 2. Install WSL if not present (requires admin)
// 3. Setup the Aurity backend in WSL
// 4. Start/stop the backend via WSL
// 5. Check backend health through WSL

#[cfg(target_os = "windows")]
use log::info;
use serde::{Deserialize, Serialize};
#[cfg(target_os = "windows")]
use std::process::Command;
#[cfg(target_os = "windows")]
use std::time::Duration;

/// WSL errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
#[allow(dead_code)] // Variants used only on Windows
pub enum WslError {
    #[error("WSL not available: {0}")]
    NotAvailable(String),
    #[error("Command failed: {0}")]
    CommandFailed(String),
    #[error("Setup error: {0}")]
    SetupError(String),
    #[error("Network error: {0}")]
    Network(String),
}

/// WSL installation status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WslStatus {
    pub installed: bool,
    pub distro: Option<String>,
    pub version: Option<u32>,
    pub backend_installed: bool,
    pub backend_running: bool,
}

/// Check if WSL is installed and get status
#[tauri::command]
pub fn check_wsl_status() -> Result<WslStatus, WslError> {
    #[cfg(target_os = "windows")]
    {
        // Check if wsl.exe exists and is functional
        let output = Command::new("wsl").args(["--status"]).output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    // WSL is installed, check for default distro
                    let distro = get_default_distro();
                    let version = get_wsl_version();
                    let backend_installed = check_backend_installed();
                    let backend_running = check_backend_running();

                    Ok(WslStatus {
                        installed: true,
                        distro,
                        version,
                        backend_installed,
                        backend_running,
                    })
                } else {
                    // WSL command exists but no distro installed
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
                        Ok(WslStatus {
                            installed: true,
                            distro: get_default_distro(),
                            version: get_wsl_version(),
                            backend_installed: check_backend_installed(),
                            backend_running: check_backend_running(),
                        })
                    }
                }
            }
            Err(_) => {
                // wsl.exe not found
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
        // On non-Windows, WSL is not applicable
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Get the default WSL distro name
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

/// Get WSL version (1 or 2)
#[cfg(target_os = "windows")]
fn get_wsl_version() -> Option<u32> {
    let output = Command::new("wsl").args(["--version"]).output().ok()?;

    if output.status.success() {
        // If --version works, it's WSL 2
        Some(2)
    } else {
        // Fallback - check with --status
        Some(1)
    }
}

/// Check if Aurity backend is installed in WSL
#[cfg(target_os = "windows")]
fn check_backend_installed() -> bool {
    let output = Command::new("wsl")
        .args([
            "--",
            "bash",
            "-c",
            "test -d /opt/aurity-backend && echo yes",
        ])
        .output();

    match output {
        Ok(result) => {
            let stdout = String::from_utf8_lossy(&result.stdout);
            stdout.trim() == "yes"
        }
        Err(_) => false,
    }
}

/// Check if backend is running in WSL
#[cfg(target_os = "windows")]
fn check_backend_running() -> bool {
    let output = Command::new("wsl")
        .args([
            "--",
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "http://localhost:7001/api/health",
        ])
        .output();

    match output {
        Ok(result) => {
            let stdout = String::from_utf8_lossy(&result.stdout);
            stdout.trim() == "200"
        }
        Err(_) => false,
    }
}

/// Install WSL with Ubuntu (requires elevation)
/// This will trigger Windows to download and install WSL
#[tauri::command]
pub fn install_wsl() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        // Use PowerShell to run wsl --install with elevation
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
            .map_err(|e| WslError::CommandFailed(format!("No se pudo iniciar la instalación de WSL: {}", e)))?;

        if output.status.success() {
            Ok("Instalación de WSL iniciada. Es posible que se requiera reiniciar el equipo.".to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let err_lower = stderr.to_lowercase();
            if err_lower.contains("cancelled") || err_lower.contains("canceled") || err_lower.contains("user") {
                Err(WslError::CommandFailed("La instalación de WSL requiere permisos de administrador. Se mostró una ventana de autorización que fue cancelada o denegada. Haz clic en 'Sí' cuando Windows te pida permiso.".to_string()))
            } else if err_lower.contains("access") || err_lower.contains("denied") || err_lower.contains("permission") {
                Err(WslError::CommandFailed("No se tienen permisos suficientes para instalar WSL. Esta operación requiere ejecutarse como administrador. Si estás en una PC corporativa, contacta a tu equipo de TI.".to_string()))
            } else {
                Err(WslError::CommandFailed(format!("La instalación de WSL falló: {}. Intenta ejecutar 'wsl --install' manualmente desde PowerShell como administrador.", stderr)))
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL installation is only available on Windows".into()))
    }
}

/// Enable WSL feature (pre-Windows 11 method)
#[tauri::command]
pub fn enable_wsl_feature() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        // Enable WSL feature via DISM
        let script = r#"
            $result = @{success=$true; message=""}
            try {
                # Check if already enabled
                $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
                $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform

                if ($wslFeature.State -eq "Enabled" -and $vmFeature.State -eq "Enabled") {
                    $result.message = "WSL features already enabled"
                } else {
                    # Enable features (requires admin)
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
            .map_err(|e| WslError::CommandFailed(format!("Failed to enable WSL feature: {}", e)))?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        Ok(stdout.to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Setup Aurity backend in WSL
/// This installs Python, dependencies, and the backend code
#[tauri::command]
pub async fn setup_wsl_backend(_app: tauri::AppHandle) -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        use tauri::Emitter;

        let emit_progress = |msg: &str| {
            let _ = _app.emit("wsl-setup-progress", msg);
            info!("{}", msg);
        };

        emit_progress("Verificando WSL...");

        // Check WSL is available
        let status = check_wsl_status()?;
        if !status.installed {
            return Err(WslError::NotAvailable("WSL no está instalado. Instálalo primero.".into()));
        }

        emit_progress("Actualizando paquetes...");

        // Update apt
        let update = Command::new("wsl")
            .args(["--", "sudo", "apt-get", "update", "-y"])
            .output()
            .map_err(|e| WslError::SetupError(format!("Failed to update apt: {}", e)))?;

        if !update.status.success() {
            let stderr = String::from_utf8_lossy(&update.stderr);
            emit_progress(&format!("Warning: apt update failed: {}", stderr));
        }

        emit_progress("Instalando Python 3.12...");

        // Install Python and pip
        let python = Command::new("wsl")
            .args([
                "--",
                "sudo",
                "apt-get",
                "install",
                "-y",
                "python3.12",
                "python3.12-venv",
                "python3-pip",
                "curl",
            ])
            .output()
            .map_err(|e| WslError::SetupError(format!("Failed to install Python: {}", e)))?;

        if !python.status.success() {
            // Try with software-properties-common for deadsnakes PPA
            emit_progress("Agregando repositorio Python...");

            let _ = Command::new("wsl")
                .args([
                    "--",
                    "sudo",
                    "apt-get",
                    "install",
                    "-y",
                    "software-properties-common",
                ])
                .output();

            let _ = Command::new("wsl")
                .args([
                    "--",
                    "sudo",
                    "add-apt-repository",
                    "-y",
                    "ppa:deadsnakes/ppa",
                ])
                .output();

            let _ = Command::new("wsl")
                .args(["--", "sudo", "apt-get", "update", "-y"])
                .output();

            let retry = Command::new("wsl")
                .args([
                    "--",
                    "sudo",
                    "apt-get",
                    "install",
                    "-y",
                    "python3.12",
                    "python3.12-venv",
                    "python3-pip",
                ])
                .output()
                .map_err(|e| WslError::SetupError(format!("Failed to install Python (retry): {}", e)))?;

            if !retry.status.success() {
                return Err(WslError::SetupError("No se pudo instalar Python 3.12".into()));
            }
        }

        emit_progress("Creando directorio del backend...");

        // Create backend directory
        let _ = Command::new("wsl")
            .args(["--", "sudo", "mkdir", "-p", "/opt/aurity-backend"])
            .output();

        let _ = Command::new("wsl")
            .args([
                "--",
                "bash",
                "-c",
                "sudo chown -R $USER:$USER /opt/aurity-backend",
            ])
            .output();

        emit_progress("Creando entorno virtual...");

        // Create virtual environment
        let venv = Command::new("wsl")
            .args([
                "--",
                "python3.12",
                "-m",
                "venv",
                "/opt/aurity-backend/.venv",
            ])
            .output()
            .map_err(|e| WslError::SetupError(format!("Failed to create venv: {}", e)))?;

        if !venv.status.success() {
            let stderr = String::from_utf8_lossy(&venv.stderr);
            return Err(WslError::SetupError(format!("Failed to create virtual environment: {}", stderr)));
        }

        emit_progress("Instalando dependencias...");

        // Install minimal dependencies
        let pip_install = Command::new("wsl")
            .args([
                "--",
                "/opt/aurity-backend/.venv/bin/pip",
                "install",
                "fastapi",
                "uvicorn[standard]",
                "httpx",
                "python-multipart",
                "pydantic",
                "pyjwt",
                "python-dotenv",
            ])
            .output()
            .map_err(|e| WslError::SetupError(format!("Failed to install dependencies: {}", e)))?;

        if !pip_install.status.success() {
            let stderr = String::from_utf8_lossy(&pip_install.stderr);
            emit_progress(&format!("Warning: Some deps failed: {}", stderr));
        }

        emit_progress("Copiando código del backend...");

        // Get Windows path to backend
        let backend_source = get_windows_backend_path();
        if let Some(win_path) = backend_source {
            // Convert Windows path to WSL path
            let wsl_source = windows_to_wsl_path(&win_path);

            // Copy backend files
            let copy = Command::new("wsl")
                .args(["--", "cp", "-r", &wsl_source, "/opt/aurity-backend/src"])
                .output();

            if let Err(e) = copy {
                emit_progress(&format!("Warning: Could not copy backend: {}", e));
            }
        }

        emit_progress("Creando script de inicio...");

        // Create startup script using backend_minimal.py
        let startup_script = r#"#!/bin/bash
cd /opt/aurity-backend
source .venv/bin/activate
export PYTHONPATH=/opt/aurity-backend
export OLLAMA_HOST=http://localhost:11434
exec python backend_minimal.py
"#;

        // Write startup script
        let write_script = Command::new("wsl")
            .args(["--", "bash", "-c",
                   &format!("echo '{}' | sudo tee /opt/aurity-backend/start.sh && sudo chmod +x /opt/aurity-backend/start.sh",
                           startup_script.replace("'", "'\"'\"'"))])
            .output();

        if let Err(e) = write_script {
            emit_progress(&format!("Warning: Could not create start script: {}", e));
        }

        emit_progress("¡Backend instalado en WSL!");

        Ok("Backend setup complete in WSL".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Get path to backend source in Windows
#[cfg(target_os = "windows")]
fn get_windows_backend_path() -> Option<String> {
    // Try to find backend relative to exe
    let exe = std::env::current_exe().ok()?;
    let mut path = exe.parent()?;

    // Go up until we find the backend directory
    for _ in 0..5 {
        let backend = path.join("backend");
        if backend.exists() {
            return Some(backend.to_string_lossy().to_string());
        }
        path = path.parent()?;
    }

    // Fallback to common development paths
    let home = dirs::home_dir()?;
    let candidates = vec![
        home.join("free-intelligence/backend"),
        home.join("projects/free-intelligence/backend"),
    ];

    for candidate in candidates {
        if candidate.exists() {
            return Some(candidate.to_string_lossy().to_string());
        }
    }

    None
}

/// Convert Windows path to WSL path
#[cfg(target_os = "windows")]
fn windows_to_wsl_path(win_path: &str) -> String {
    // C:\Users\... -> /mnt/c/Users/...
    let path = win_path.replace('\\', "/");
    match path.as_bytes() {
        [drive_letter, b':', b'/', rest @ ..] if drive_letter.is_ascii_alphabetic() => {
            let drive = (*drive_letter as char).to_ascii_lowercase();
            format!("/mnt/{}/{}", drive, std::str::from_utf8(rest).unwrap_or(""))
        }
        [drive_letter, b':', rest @ ..] if drive_letter.is_ascii_alphabetic() => {
            let drive = (*drive_letter as char).to_ascii_lowercase();
            let remainder = std::str::from_utf8(rest).unwrap_or("");
            format!("/mnt/{}/{}", drive, remainder.trim_start_matches('/'))
        }
        _ => path,
    }
}

/// Start the backend in WSL
#[tauri::command]
pub fn start_wsl_backend() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        // Start backend in background via WSL
        let output = Command::new("wsl")
            .args([
                "--",
                "bash",
                "-c",
                "nohup /opt/aurity-backend/start.sh > /opt/aurity-backend/backend.log 2>&1 &",
            ])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to start backend: {}", e)))?;

        if output.status.success() {
            // Wait a moment for startup
            std::thread::sleep(Duration::from_secs(2));

            // Check if it's running
            if check_backend_running() {
                Ok("Backend started successfully".to_string())
            } else {
                Ok("Backend starting... (may take a few seconds)".to_string())
            }
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(WslError::CommandFailed(format!("Failed to start backend: {}", stderr)))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Stop the backend in WSL
#[tauri::command]
pub fn stop_wsl_backend() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("wsl")
            .args(["--", "pkill", "-f", "uvicorn.*backend"])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to stop backend: {}", e)))?;

        Ok("Backend stopped".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Check backend health via WSL
#[tauri::command]
pub async fn check_wsl_backend_health() -> Result<bool, WslError> {
    #[cfg(target_os = "windows")]
    {
        // Try to reach the backend directly (WSL shares localhost with Windows)
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(3))
            .build()
            .map_err(|e| WslError::Network(e.to_string()))?;

        match client.get("http://127.0.0.1:7001/api/health").send().await {
            Ok(response) => Ok(response.status().is_success()),
            Err(_) => Ok(false),
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}

/// Get WSL backend logs
#[tauri::command]
pub fn get_wsl_backend_logs(_lines: Option<u32>) -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let n = _lines.unwrap_or(50);
        let output = Command::new("wsl")
            .args([
                "--",
                "tail",
                "-n",
                &n.to_string(),
                "/opt/aurity-backend/backend.log",
            ])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to get logs: {}", e)))?;

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable("WSL is only available on Windows".into()))
    }
}
