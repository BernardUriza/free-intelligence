// Aurity Desktop - Main Entry Point
//
// This application manages:
// 1. FastAPI backend as a sidecar process with DYNAMIC port allocation
// 2. Tauri webview for the frontend
// 3. Splashscreen while loading
// 4. Health checks before showing UI
// 5. Proper lifecycle management (cleanup on exit)
// 6. First-run config bootstrap (extracts templates to user data dir)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod auth;
mod fi_monitor;
mod license;
mod templates;
mod wsl;

use auth::AuthState;
use serde::{Deserialize, Serialize};
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tauri::{Emitter, Listener, Manager};
use tauri_plugin_deep_link::DeepLinkExt;
use tauri_plugin_shell::ShellExt;
use tokio::time::sleep;

/// Global state for backend
struct BackendState {
    port: AtomicU16,
    is_ready: AtomicBool,
}

/// Find an available port based on build mode
/// Port allocation:
///   - 7001: Desktop (fixed, both dev and release)
///   - 7002-7050: Fallback if 7001 is busy
fn find_available_port() -> Option<u16> {
    // Always try 7001 first (frontend expects this)
    let port = 7001;
    if TcpListener::bind(("127.0.0.1", port)).is_ok() {
        return Some(port);
    }
    // Fallback to dynamic if 7001 is busy
    for p in 7002..7050 {
        if TcpListener::bind(("127.0.0.1", p)).is_ok() {
            return Some(p);
        }
    }
    None
}

/// Check if the backend is responding to health checks
async fn check_backend_health(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{}/api/health", port);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();

    match client.get(&url).send().await {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Emit loading status to splashscreen
fn emit_status(app: &tauri::AppHandle, message: &str) {
    let _ = app.emit("loading-status", message);
}

/// Get the backend URL (with dynamic port)
#[tauri::command]
fn get_backend_url(state: tauri::State<'_, Arc<BackendState>>) -> String {
    let port = state.port.load(Ordering::SeqCst);
    format!("http://127.0.0.1:{}", port)
}

/// Check if backend is ready
#[tauri::command]
fn get_backend_status(state: tauri::State<'_, Arc<BackendState>>) -> bool {
    state.is_ready.load(Ordering::SeqCst)
}

/// Check if Ollama is running locally
#[tauri::command]
async fn check_ollama_status() -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    match client.get("http://localhost:11434/api/tags").send().await {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

/// Ensure Ollama/Edge infrastructure is running
/// On Windows: runs ollama-tunnel.ps1 start
/// On macOS/Linux: runs ollama-tunnel.sh start
#[tauri::command]
async fn ensure_edge_infrastructure(app: tauri::AppHandle) -> Result<String, String> {
    // First check if Ollama is already running
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    let ollama_running = client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    if ollama_running {
        return Ok("Ollama already running".to_string());
    }

    // Ollama not running - execute the tunnel script
    println!("[Aurity] Ollama not running, starting edge infrastructure...");

    // Find the scripts directory (relative to app or project root)
    let scripts_dir = find_scripts_dir();

    #[cfg(target_os = "windows")]
    {
        use std::process::Command;

        let script_path = scripts_dir.join("ollama-tunnel.ps1");
        if !script_path.exists() {
            return Err(format!("Script not found: {:?}", script_path));
        }

        let output = Command::new("powershell")
            .args([
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                &script_path.to_string_lossy(),
                "start",
            ])
            .current_dir(&scripts_dir)
            .output()
            .map_err(|e| format!("Failed to execute script: {}", e))?;

        if output.status.success() {
            Ok("Edge infrastructure started (Windows)".to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("Script failed: {}", stderr))
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        use std::process::Command;

        let script_path = scripts_dir.join("ollama-tunnel.sh");
        if !script_path.exists() {
            return Err(format!("Script not found: {:?}", script_path));
        }

        let output = Command::new("bash")
            .args([&script_path.to_string_lossy().to_string(), "start"])
            .current_dir(&scripts_dir)
            .output()
            .map_err(|e| format!("Failed to execute script: {}", e))?;

        if output.status.success() {
            Ok("Edge infrastructure started (Unix)".to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(format!("Script failed: {}", stderr))
        }
    }
}

/// Find the scripts directory
fn find_scripts_dir() -> PathBuf {
    // Try relative paths from different locations
    let candidates = vec![
        PathBuf::from("scripts"),
        PathBuf::from("../../../scripts"),
        PathBuf::from("../../scripts"),
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("scripts")))
            .unwrap_or_default(),
    ];

    for candidate in candidates {
        if candidate.exists() && candidate.is_dir() {
            return candidate;
        }
    }

    // Fallback
    PathBuf::from("scripts")
}

// =============================================================================
// WINDOWS AUTOSTART
// =============================================================================

const AUTOSTART_KEY: &str = "AurityDesktop";

/// Internal function to setup Windows autostart
#[cfg(target_os = "windows")]
fn setup_windows_autostart_internal() -> Result<bool, String> {
    use std::process::Command;

    let exe_path = std::env::current_exe().map_err(|e| format!("Failed to get exe path: {}", e))?;

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
        .map_err(|e| format!("Failed to execute reg: {}", e))?;

    if output.status.success() {
        Ok(true)
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Failed to add registry key: {}", stderr))
    }
}

/// Setup Windows autostart (adds to registry Run key)
#[tauri::command]
fn setup_windows_autostart() -> Result<bool, String> {
    #[cfg(target_os = "windows")]
    {
        let result = setup_windows_autostart_internal();
        if result.is_ok() {
            println!("[Aurity] Windows autostart enabled");
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
fn remove_windows_autostart() -> Result<bool, String> {
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
            .map_err(|e| format!("Failed to execute reg: {}", e))?;

        if output.status.success() {
            println!("[Aurity] Windows autostart disabled");
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
fn check_windows_autostart() -> Result<bool, String> {
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
            .map_err(|e| format!("Failed to execute reg: {}", e))?;

        Ok(output.status.success())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Ok(false)
    }
}

/// Python installation status
#[derive(Serialize)]
struct PythonStatus {
    installed: bool,
    version: Option<String>,
    pip_available: bool,
    fi_monitor_deps_installed: bool,
}

/// Check Python 3.14+ installation and dependencies
#[tauri::command]
async fn check_python_installation() -> Result<PythonStatus, String> {
    use std::process::Command;

    // Check python --version
    let version_output = Command::new("python").arg("--version").output();

    let (installed, version) = match version_output {
        Ok(output) if output.status.success() => {
            let v = String::from_utf8_lossy(&output.stdout).to_string();
            (true, Some(v.trim().to_string()))
        }
        _ => (false, None),
    };

    if !installed {
        return Ok(PythonStatus {
            installed: false,
            version: None,
            pip_available: false,
            fi_monitor_deps_installed: false,
        });
    }

    // Check pip
    let pip_output = Command::new("python")
        .args(["-m", "pip", "--version"])
        .output();
    let pip_available = pip_output.map(|o| o.status.success()).unwrap_or(false);

    // Check fi-monitor deps (fastapi, uvicorn, httpx, sentence_transformers)
    let deps_check = Command::new("python")
        .args([
            "-c",
            "import fastapi, uvicorn, httpx, sentence_transformers",
        ])
        .output();
    let fi_monitor_deps_installed = deps_check.map(|o| o.status.success()).unwrap_or(false);

    Ok(PythonStatus {
        installed,
        version,
        pip_available,
        fi_monitor_deps_installed,
    })
}

/// First-run status for frontend wizard
#[derive(Serialize)]
struct FirstRunStatus {
    config_initialized: bool,
    ollama_available: bool,
    data_dir: String,
}

/// Check first-run status (for frontend wizard)
#[tauri::command]
async fn check_first_run_status(app: tauri::AppHandle) -> Result<FirstRunStatus, String> {
    let data_dir = get_data_dir(&app)?;
    let config_exists = data_dir.join("config/fi.policy.yaml").exists();

    // Check Ollama synchronously for simplicity
    let ollama_ok = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    Ok(FirstRunStatus {
        config_initialized: config_exists,
        ollama_available: ollama_ok,
        data_dir: data_dir.to_string_lossy().to_string(),
    })
}

// =============================================================================
// WIZARD STATE PERSISTENCE
// =============================================================================

/// Wizard state persisted to filesystem (~/.aurity/config/wizard-state.json)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WizardState {
    pub version: u32,
    pub desktop_setup_completed: bool,
    pub desktop_setup_completed_at: Option<String>,
    pub fi_monitor_installed: Option<bool>,
}

/// Get the path to wizard state file
fn get_wizard_state_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let data_dir = get_data_dir(app)?;
    Ok(data_dir.join("config").join("wizard-state.json"))
}

/// Get wizard state from filesystem
#[tauri::command]
fn get_wizard_state(app: tauri::AppHandle) -> Result<WizardState, String> {
    let state_path = get_wizard_state_path(&app)?;

    if !state_path.exists() {
        // File doesn't exist - return default state (wizard not completed)
        return Ok(WizardState::default());
    }

    // Verify it's a regular file, not a symlink (security check)
    if state_path.is_symlink() {
        return Err("Security: wizard state file is a symlink, refusing to read".to_string());
    }

    let content = fs::read_to_string(&state_path)
        .map_err(|e| format!("Failed to read wizard state: {}", e))?;

    serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse wizard state: {}", e))
}

/// Mark desktop setup as complete
#[tauri::command]
fn mark_desktop_setup_complete(
    app: tauri::AppHandle,
    fi_monitor_installed: bool,
) -> Result<WizardState, String> {
    let state_path = get_wizard_state_path(&app)?;

    // Ensure parent directory exists
    if let Some(parent) = state_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config directory: {}", e))?;
    }

    // Create new state
    let state = WizardState {
        version: 1,
        desktop_setup_completed: true,
        desktop_setup_completed_at: Some(chrono::Utc::now().to_rfc3339()),
        fi_monitor_installed: Some(fi_monitor_installed),
    };

    // Serialize to JSON
    let content = serde_json::to_string_pretty(&state)
        .map_err(|e| format!("Failed to serialize wizard state: {}", e))?;

    // Write atomically
    atomic_write(&state_path, content.as_bytes())?;

    println!(
        "[Aurity] Wizard state saved: desktop_setup_completed=true, fi_monitor_installed={}",
        fi_monitor_installed
    );

    Ok(state)
}

/// Reset wizard state (for development/testing)
#[tauri::command]
fn reset_wizard_state(app: tauri::AppHandle) -> Result<bool, String> {
    let state_path = get_wizard_state_path(&app)?;

    if state_path.exists() {
        fs::remove_file(&state_path)
            .map_err(|e| format!("Failed to delete wizard state: {}", e))?;
        println!("[Aurity] Wizard state reset (file deleted)");
        Ok(true)
    } else {
        println!("[Aurity] Wizard state reset (file didn't exist)");
        Ok(false)
    }
}

/// Get the user data directory for Aurity
fn get_data_dir(_app: &tauri::AppHandle) -> Result<PathBuf, String> {
    // Use ~/.aurity for consistency with backend expectations
    // Note: _app parameter kept for potential future use with tauri::PathResolver
    let home = dirs::home_dir().ok_or("Could not find home directory")?;
    Ok(home.join(".aurity"))
}

/// Atomically write a file: write to .tmp, then rename
/// This prevents partial writes and is safer against TOCTOU attacks
fn atomic_write(path: &PathBuf, content: &[u8]) -> Result<(), String> {
    let tmp_path = path.with_extension("tmp");

    // Write to temporary file
    fs::write(&tmp_path, content)
        .map_err(|e| format!("Failed to write temp file {:?}: {}", tmp_path, e))?;

    // Atomically rename to final path
    fs::rename(&tmp_path, path)
        .map_err(|e| format!("Failed to rename {:?} to {:?}: {}", tmp_path, path, e))?;

    Ok(())
}

/// Validate filename doesn't contain path separators (security check)
fn is_safe_filename(filename: &str) -> bool {
    !filename.contains('/') && !filename.contains('\\') && !filename.contains("..")
}

/// Bootstrap configuration files on first run
/// Extracts embedded templates to user data directory
///
/// Security measures:
/// - Atomic writes (write to .tmp, then rename) to prevent partial state
/// - Filename validation to prevent path traversal
/// - Symlink detection to prevent symlink attacks
fn bootstrap_config(app: &tauri::AppHandle) -> Result<bool, String> {
    let data_dir = get_data_dir(app)?;
    let config_dir = data_dir.join("config");
    let personas_dir = config_dir.join("personas");
    let storage_dir = data_dir.join("storage");
    let policy_path = config_dir.join("fi.policy.yaml");

    // Check if already initialized (atomic check - file either exists or doesn't)
    if policy_path.exists() {
        // Additional safety: verify it's a regular file, not a symlink
        if policy_path.is_symlink() {
            return Err("Security: config file is a symlink, refusing to proceed".to_string());
        }
        println!("[Aurity] Config already initialized at {:?}", config_dir);
        return Ok(false); // Not first run
    }

    println!(
        "[Aurity] First run detected - bootstrapping config to {:?}",
        data_dir
    );

    // Create directories (these are idempotent operations)
    fs::create_dir_all(&config_dir).map_err(|e| format!("Failed to create config dir: {}", e))?;
    fs::create_dir_all(&personas_dir)
        .map_err(|e| format!("Failed to create personas dir: {}", e))?;
    fs::create_dir_all(&storage_dir).map_err(|e| format!("Failed to create storage dir: {}", e))?;

    // Verify directories are not symlinks (security check)
    if config_dir.is_symlink() || personas_dir.is_symlink() || storage_dir.is_symlink() {
        return Err("Security: one or more config directories are symlinks".to_string());
    }

    // Write all persona templates first (so policy is written last as completion marker)
    for (filename, content) in templates::PERSONAS {
        // Validate filename to prevent path traversal
        if !is_safe_filename(filename) {
            return Err(format!(
                "Security: invalid filename in templates: {}",
                filename
            ));
        }
        let persona_path = personas_dir.join(filename);
        atomic_write(&persona_path, content.as_bytes())?;
    }

    // Write policy template LAST (serves as "initialization complete" marker)
    atomic_write(&policy_path, templates::POLICY.as_bytes())?;

    println!("[Aurity] Config bootstrapped successfully!");
    println!("[Aurity]   - Policy: {:?}", policy_path);
    println!("[Aurity]   - Personas: {} files", templates::PERSONAS.len());

    Ok(true) // First run completed
}

fn main() {
    let backend_state = Arc::new(BackendState {
        port: AtomicU16::new(0),
        is_ready: AtomicBool::new(false),
    });

    let auth_state = AuthState::default();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        // Note: single-instance plugin removed due to Tauri 2.x config issues
        // Deep links on macOS handled via on_open_url() below, Windows/Linux can add back later
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(backend_state.clone())
        .manage(auth_state)
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state = backend_state.clone();

            // Register deep link handler for OAuth callbacks (macOS)
            #[cfg(target_os = "macos")]
            {
                let dl_handle = app_handle.clone();
                app.deep_link().on_open_url(move |event| {
                    for url in event.urls() {
                        let url_str = url.to_string();
                        if url_str.starts_with("aurity://") {
                            println!("[Aurity] Deep link received: {}", url_str);
                            let _ = dl_handle.emit("deep-link-received", url_str);
                        }
                    }
                });
            }

            // On Linux/Windows, check CLI args for deep link (first launch)
            #[cfg(not(target_os = "macos"))]
            {
                for arg in std::env::args() {
                    if arg.starts_with("aurity://") {
                        println!("[Aurity] Deep link from args: {}", arg);
                        let _ = app_handle.emit("deep-link-received", arg);
                    }
                }
            }

            // Step 0: Bootstrap config on first run (BEFORE spawning backend)
            emit_status(&app_handle, "Verificando configuración...");
            match bootstrap_config(&app_handle) {
                Ok(true) => {
                    println!("[Aurity] First run - config bootstrapped");
                    let _ = app_handle.emit("first-run-detected", ());

                    // DISABLED: Only FI-monitor should autostart, not Aurity Desktop
                    // User can manually enable autostart from settings if needed
                    // #[cfg(target_os = "windows")]
                    // {
                    //     emit_status(&app_handle, "Configurando inicio automático...");
                    //     match setup_windows_autostart_internal() {
                    //         Ok(true) => println!("[Aurity] Windows autostart configured"),
                    //         Ok(false) => println!("[Aurity] Windows autostart skipped"),
                    //         Err(e) => eprintln!("[Aurity] WARNING: Failed to setup autostart: {}", e),
                    //     }
                    // }
                }
                Ok(false) => {
                    println!("[Aurity] Config already exists");
                }
                Err(e) => {
                    eprintln!("[Aurity] WARNING: Failed to bootstrap config: {}", e);
                    // Continue anyway - backend might still work
                }
            }

            // Spawn async task to start backend
            tauri::async_runtime::spawn(async move {
                // Step 1: Find available port
                emit_status(&app_handle, "Buscando puerto disponible...");

                let port = match find_available_port() {
                    Some(p) => {
                        println!("[Aurity] Selected port {} for backend", p);
                        p
                    }
                    None => {
                        eprintln!("[Aurity] ERROR: No available ports in range 7001-7999");
                        emit_status(&app_handle, "Error: No hay puertos disponibles");
                        return;
                    }
                };

                state.port.store(port, Ordering::SeqCst);

                // Step 2: Start the sidecar with the selected port
                emit_status(&app_handle, "Iniciando backend de IA...");

                let shell = app_handle.shell();
                let sidecar_result = shell
                    .sidecar("aurity-backend")
                    .expect("Failed to create sidecar command")
                    .args(["--port", &port.to_string()])
                    .spawn();

                match sidecar_result {
                    Ok((mut rx, _child)) => {
                        println!("[Aurity] Backend sidecar started");

                        // The tauri-plugin-process automatically handles cleanup on app exit

                        // Log sidecar output in background
                        let status_handle = app_handle.clone();
                        tauri::async_runtime::spawn(async move {
                            while let Some(event) = rx.recv().await {
                                match event {
                                    tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                                        let line_str = String::from_utf8_lossy(&line);
                                        println!("[backend] {}", line_str);

                                        // Detect when uvicorn is ready
                                        if line_str.contains("Uvicorn running")
                                            || line_str.contains("Application startup complete")
                                        {
                                            emit_status(&status_handle, "Backend iniciado!");
                                        }
                                    }
                                    tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                                        eprintln!(
                                            "[backend-err] {}",
                                            String::from_utf8_lossy(&line)
                                        );
                                    }
                                    tauri_plugin_shell::process::CommandEvent::Terminated(
                                        status,
                                    ) => {
                                        println!("[Aurity] Backend terminated: {:?}", status);
                                        break;
                                    }
                                    _ => {}
                                }
                            }
                        });

                        // Step 3: Show main window IMMEDIATELY (don't wait for health checks)
                        // Frontend will show loading/setup wizard while backend starts
                        println!("[Aurity] Showing main window (backend starting in background)");

                        // Inject backend URL into main window
                        if let Some(main_window) = app_handle.get_webview_window("main") {
                            let js = format!(
                                "window.__AURITY_BACKEND_URL__ = 'http://127.0.0.1:{}';",
                                port
                            );
                            let _ = main_window.eval(&js);

                            // Show main window immediately
                            let _ = main_window.show();
                            let _ = main_window.set_focus();

                            // Wait for frontend ready signal before closing splash
                            let splash_handle = app_handle.clone();
                            main_window.listen("frontend-ready", move |_| {
                                println!("[Aurity] Frontend ready - closing splash");
                                if let Some(splash) = splash_handle.get_webview_window("splashscreen") {
                                    let _ = splash.close();
                                }
                            });

                            // Fallback: close splash after 5s if frontend doesn't respond
                            let splash_fallback = app_handle.clone();
                            tauri::async_runtime::spawn(async move {
                                tokio::time::sleep(Duration::from_secs(5)).await;
                                if let Some(splash) = splash_fallback.get_webview_window("splashscreen") {
                                    println!("[Aurity] Fallback: closing splash after timeout");
                                    let _ = splash.close();
                                }
                            });
                        }

                        // Step 4: Health check in BACKGROUND (non-blocking)
                        emit_status(&app_handle, "Verificando backend...");

                        let mut attempts = 0;
                        let max_attempts = 60; // 30 seconds total (500ms * 60)

                        while attempts < max_attempts {
                            if check_backend_health(port).await {
                                state.is_ready.store(true, Ordering::SeqCst);
                                println!("[Aurity] Backend is healthy on port {}", port);

                                // Emit ready event (frontend can use this to hide loading states)
                                let _ = app_handle.emit(
                                    "backend-ready",
                                    serde_json::json!({
                                        "port": port
                                    }),
                                );
                                break;
                            }

                            attempts += 1;
                            sleep(Duration::from_millis(500)).await;

                            // Update status every 2 seconds
                            if attempts % 4 == 0 {
                                emit_status(
                                    &app_handle,
                                    &format!("Iniciando backend... {}s", attempts / 2),
                                );
                            }
                        }

                        // Report error if health check failed (but main window is already visible)
                        if !state.is_ready.load(Ordering::SeqCst) {
                            emit_status(&app_handle, "Error: Backend no responde");
                            eprintln!(
                                "[Aurity] ERROR: Backend failed to respond after {} attempts",
                                max_attempts
                            );
                            let _ = app_handle.emit("backend-error", "Backend failed to start");
                        }
                    }
                    Err(e) => {
                        eprintln!("[Aurity] Failed to spawn sidecar: {}", e);
                        emit_status(&app_handle, &format!("Error: {}", e));

                        // In dev mode, continue anyway without backend
                        #[cfg(debug_assertions)]
                        {
                            println!("[Aurity] DEV MODE: Continuing without backend sidecar");
                            sleep(Duration::from_secs(2)).await;
                            emit_status(&app_handle, "Modo desarrollo (sin backend)");

                            // Show main window anyway
                            if let Some(main_window) = app_handle.get_webview_window("main") {
                                let js = format!(
                                    "window.__AURITY_BACKEND_URL__ = 'http://127.0.0.1:{}';",
                                    port
                                );
                                let _ = main_window.eval(&js);
                                let _ = main_window.eval("window.__AURITY_DEV_MODE__ = true;");
                                let _ = main_window.show();
                                let _ = main_window.set_focus();
                            }

                            // Close splashscreen
                            if let Some(splash) = app_handle.get_webview_window("splashscreen") {
                                let _ = splash.close();
                            }
                        }
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_backend_status,
            check_ollama_status,
            ensure_edge_infrastructure,
            check_first_run_status,
            // Wizard state persistence
            get_wizard_state,
            mark_desktop_setup_complete,
            reset_wizard_state,
            // Windows autostart
            setup_windows_autostart,
            remove_windows_autostart,
            check_windows_autostart,
            // Python verification
            check_python_installation,
            // FI Monitor integration
            fi_monitor::check_fi_monitor_installed,
            fi_monitor::launch_fi_monitor,
            fi_monitor::download_fi_monitor,
            fi_monitor::install_fi_monitor_silent,
            fi_monitor::install_fi_monitor_full,
            // WSL integration (Windows backend)
            wsl::check_wsl_status,
            wsl::install_wsl,
            wsl::enable_wsl_feature,
            wsl::setup_wsl_backend,
            wsl::start_wsl_backend,
            wsl::stop_wsl_backend,
            wsl::check_wsl_backend_health,
            wsl::get_wsl_backend_logs,
            // Auth0 OAuth commands
            auth::configure_auth0,
            auth::start_auth_flow,
            auth::handle_auth_callback,
            auth::get_stored_tokens,
            auth::refresh_tokens,
            auth::clear_tokens,
            auth::is_token_expired,
            auth::get_token_expiry,
            // License commands
            license::validate_license_key,
            license::activate_license_key,
            license::get_current_license_status,
            license::get_license_auth0_config,
            license::check_feature_enabled,
            license::clear_stored_license,
            // License renewal commands
            license::check_license_renewal_status,
            license::request_license_renewal,
            license::register_license_for_renewal,
            // License file import commands
            license::import_license_from_file,
            license::has_valid_license,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running Aurity Desktop");
}
