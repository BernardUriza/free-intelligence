// WSL Backend — setup, start, stop, health checks, and log retrieval
// for the Aurity backend running inside WSL.

use super::WslError;

#[cfg(target_os = "windows")]
use super::{
    DEFAULT_LOG_LINES, HEALTH_ENDPOINT, OLLAMA_HOST, POST_START_DELAY_SECS, WSL_BACKEND_DIR,
    WSL_BACKEND_PORT, WSL_HEALTH_TIMEOUT_SECS,
};

#[cfg(target_os = "windows")]
use log::info;
#[cfg(target_os = "windows")]
use std::process::Command;
#[cfg(target_os = "windows")]
use std::time::Duration;

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Setup Aurity backend in WSL.
/// Installs Python, dependencies, copies source, and creates a startup script.
#[tauri::command]
pub async fn setup_wsl_backend(_app: tauri::AppHandle) -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        use super::paths;
        use tauri::Emitter;

        let emit_progress = |msg: &str| {
            let _ = _app.emit("wsl-setup-progress", msg);
            info!("{}", msg);
        };

        // ── Verify WSL ─────────────────────────────────────────────────
        emit_progress("Verificando WSL...");
        let status = super::detection::check_wsl_status()?;
        if !status.installed {
            return Err(WslError::NotAvailable(
                "WSL no está instalado. Instálalo primero.".into(),
            ));
        }

        // ── apt update ─────────────────────────────────────────────────
        emit_progress("Actualizando paquetes...");
        run_apt_update(&emit_progress);

        // ── Python 3.12 ────────────────────────────────────────────────
        emit_progress("Instalando Python 3.12...");
        install_python(&emit_progress)?;

        // ── Backend directory ──────────────────────────────────────────
        emit_progress("Creando directorio del backend...");
        create_backend_dir();

        // ── Virtual environment ────────────────────────────────────────
        emit_progress("Creando entorno virtual...");
        create_venv()?;

        // ── pip install ────────────────────────────────────────────────
        emit_progress("Instalando dependencias...");
        install_deps(&emit_progress);

        // ── Copy backend source ────────────────────────────────────────
        emit_progress("Copiando código del backend...");
        if let Some(win_path) = paths::get_windows_backend_path() {
            let wsl_source = paths::windows_to_wsl_path(&win_path);
            let copy = Command::new("wsl")
                .args([
                    "--",
                    "cp",
                    "-r",
                    &wsl_source,
                    &format!("{}/src", WSL_BACKEND_DIR),
                ])
                .output();
            if let Err(e) = copy {
                emit_progress(&format!("Warning: Could not copy backend: {}", e));
            }
        }

        // ── Startup script ─────────────────────────────────────────────
        emit_progress("Creando script de inicio...");
        create_startup_script(&emit_progress);

        emit_progress("¡Backend instalado en WSL!");
        Ok("Backend setup complete in WSL".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

/// Start the backend in WSL (background process).
#[tauri::command]
pub fn start_wsl_backend() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let start_cmd = format!(
            "nohup {}/start.sh > {}/backend.log 2>&1 &",
            WSL_BACKEND_DIR, WSL_BACKEND_DIR
        );
        let output = Command::new("wsl")
            .args(["--", "bash", "-c", &start_cmd])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to start backend: {}", e)))?;

        if output.status.success() {
            std::thread::sleep(Duration::from_secs(POST_START_DELAY_SECS));

            if check_backend_running() {
                Ok("Backend started successfully".to_string())
            } else {
                Ok("Backend starting... (may take a few seconds)".to_string())
            }
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(WslError::CommandFailed(format!(
                "Failed to start backend: {}",
                stderr
            )))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

/// Stop the backend in WSL.
#[tauri::command]
pub fn stop_wsl_backend() -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let _output = Command::new("wsl")
            .args(["--", "pkill", "-f", "uvicorn.*backend"])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to stop backend: {}", e)))?;

        Ok("Backend stopped".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

/// Check backend health via WSL (WSL shares localhost with Windows).
#[tauri::command]
pub async fn check_wsl_backend_health() -> Result<bool, WslError> {
    #[cfg(target_os = "windows")]
    {
        let url = format!(
            "http://127.0.0.1:{}{}",
            WSL_BACKEND_PORT, HEALTH_ENDPOINT
        );
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(WSL_HEALTH_TIMEOUT_SECS))
            .build()
            .map_err(|e| WslError::Network(e.to_string()))?;

        match client.get(&url).send().await {
            Ok(response) => Ok(response.status().is_success()),
            Err(_) => Ok(false),
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

/// Get WSL backend logs.
#[tauri::command]
pub fn get_wsl_backend_logs(_lines: Option<u32>) -> Result<String, WslError> {
    #[cfg(target_os = "windows")]
    {
        let n = _lines.unwrap_or(DEFAULT_LOG_LINES);
        let log_path = format!("{}/backend.log", WSL_BACKEND_DIR);
        let output = Command::new("wsl")
            .args(["--", "tail", "-n", &n.to_string(), &log_path])
            .output()
            .map_err(|e| WslError::CommandFailed(format!("Failed to get logs: {}", e)))?;

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err(WslError::NotAvailable(
            "WSL is only available on Windows".into(),
        ))
    }
}

// =============================================================================
// INTERNAL HELPERS (used by detection.rs too via pub(crate))
// =============================================================================

/// Check if the Aurity backend directory exists inside WSL.
#[cfg(target_os = "windows")]
pub(crate) fn check_backend_installed() -> bool {
    let test_cmd = format!("test -d {} && echo yes", WSL_BACKEND_DIR);
    let output = Command::new("wsl")
        .args(["--", "bash", "-c", &test_cmd])
        .output();

    match output {
        Ok(result) => {
            let stdout = String::from_utf8_lossy(&result.stdout);
            stdout.trim() == "yes"
        }
        Err(_) => false,
    }
}

/// Check if the backend process is responding to health checks inside WSL.
#[cfg(target_os = "windows")]
pub(crate) fn check_backend_running() -> bool {
    let health_url = format!("http://localhost:{}{}", WSL_BACKEND_PORT, HEALTH_ENDPOINT);
    let output = Command::new("wsl")
        .args([
            "--",
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            &health_url,
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

// =============================================================================
// SETUP STEP HELPERS (keep setup_wsl_backend readable)
// =============================================================================

#[cfg(target_os = "windows")]
fn run_apt_update(emit: &dyn Fn(&str)) {
    let update = Command::new("wsl")
        .args(["--", "sudo", "apt-get", "update", "-y"])
        .output();

    if let Ok(result) = update {
        if !result.status.success() {
            let stderr = String::from_utf8_lossy(&result.stderr);
            emit(&format!("Warning: apt update failed: {}", stderr));
        }
    }
}

#[cfg(target_os = "windows")]
fn install_python(emit: &dyn Fn(&str)) -> Result<(), WslError> {
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
        // Try with deadsnakes PPA
        emit("Agregando repositorio Python...");
        install_python_via_ppa()?;
    }
    Ok(())
}

#[cfg(target_os = "windows")]
fn install_python_via_ppa() -> Result<(), WslError> {
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
        return Err(WslError::SetupError(
            "No se pudo instalar Python 3.12".into(),
        ));
    }
    Ok(())
}

#[cfg(target_os = "windows")]
fn create_backend_dir() {
    let _ = Command::new("wsl")
        .args(["--", "sudo", "mkdir", "-p", WSL_BACKEND_DIR])
        .output();

    let chown_cmd = format!("sudo chown -R $USER:$USER {}", WSL_BACKEND_DIR);
    let _ = Command::new("wsl")
        .args(["--", "bash", "-c", &chown_cmd])
        .output();
}

#[cfg(target_os = "windows")]
fn create_venv() -> Result<(), WslError> {
    let venv_path = format!("{}/.venv", WSL_BACKEND_DIR);
    let venv = Command::new("wsl")
        .args(["--", "python3.12", "-m", "venv", &venv_path])
        .output()
        .map_err(|e| WslError::SetupError(format!("Failed to create venv: {}", e)))?;

    if !venv.status.success() {
        let stderr = String::from_utf8_lossy(&venv.stderr);
        return Err(WslError::SetupError(format!(
            "Failed to create virtual environment: {}",
            stderr
        )));
    }
    Ok(())
}

#[cfg(target_os = "windows")]
fn install_deps(emit: &dyn Fn(&str)) {
    let pip_path = format!("{}/.venv/bin/pip", WSL_BACKEND_DIR);
    let pip_install = Command::new("wsl")
        .args([
            "--",
            &pip_path,
            "install",
            "fastapi",
            "uvicorn[standard]",
            "httpx",
            "python-multipart",
            "pydantic",
            "pyjwt",
            "python-dotenv",
        ])
        .output();

    if let Ok(result) = pip_install {
        if !result.status.success() {
            let stderr = String::from_utf8_lossy(&result.stderr);
            emit(&format!("Warning: Some deps failed: {}", stderr));
        }
    }
}

#[cfg(target_os = "windows")]
fn create_startup_script(emit: &dyn Fn(&str)) {
    let startup_script = format!(
        r#"#!/bin/bash
cd {dir}
source .venv/bin/activate
export PYTHONPATH={dir}
export OLLAMA_HOST={ollama}
exec python backend_minimal.py
"#,
        dir = WSL_BACKEND_DIR,
        ollama = OLLAMA_HOST,
    );

    let write_cmd = format!(
        "echo '{}' | sudo tee {}/start.sh && sudo chmod +x {}/start.sh",
        startup_script.replace('\'', "'\"'\"'"),
        WSL_BACKEND_DIR,
        WSL_BACKEND_DIR
    );

    let write_script = Command::new("wsl")
        .args(["--", "bash", "-c", &write_cmd])
        .output();

    if let Err(e) = write_script {
        emit(&format!("Warning: Could not create start script: {}", e));
    }
}
