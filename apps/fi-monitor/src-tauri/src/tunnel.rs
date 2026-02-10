use crate::config::save_config;
use crate::ollama::check_ollama;
use crate::state::*;
use regex::Regex;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::time::Duration;
use tauri::Emitter;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// ============================================================================
// Tunnel Management
// ============================================================================

#[tauri::command]
pub(crate) async fn start_tunnel(
    app: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<String, String> {
    // Si hay tunnel local corriendo, detenerlo primero
    let current_mode = *state.tunnel_mode.lock().unwrap();
    if current_mode == TunnelMode::Local && *state.tunnel_running.lock().unwrap() {
        println!("[FI Monitor] Switching from local tunnel to cloudflared...");
        stop_tunnel_internal(Arc::clone(&*state))?;
    }

    // Iniciar cloudflared REAL (acceso remoto)
    start_tunnel_cloudflared_internal(app, Arc::clone(&*state)).await
}

#[tauri::command]
pub(crate) async fn stop_tunnel(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    let mode = *state.tunnel_mode.lock().unwrap();

    // Detener tunnel actual
    stop_tunnel_internal(Arc::clone(&*state))?;

    // Si era cloudflared, volver a modo local automaticamente
    if mode == TunnelMode::Cloudflared {
        println!("[FI Monitor] Returning to local tunnel mode...");
        start_tunnel_local(Arc::clone(&*state))?;
    }

    Ok(true)
}

/// Internal function to stop tunnel without restarting local mode
fn stop_tunnel_internal(state: Arc<AppState>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping tunnel...");

    let mode = *state.tunnel_mode.lock().unwrap();

    // Solo matar proceso si es cloudflared
    if mode == TunnelMode::Cloudflared {
        if let Some(pid) = state.tunnel_process.lock().unwrap().take() {
            #[cfg(target_os = "windows")]
            {
                let _ = Command::new("taskkill")
                    .args(["/F", "/PID", &pid.to_string()])
                    .output();
            }
            #[cfg(not(target_os = "windows"))]
            {
                let _ = Command::new("kill").arg(pid.to_string()).output();
            }
        }
        #[cfg(target_os = "windows")]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/IM", "cloudflared.exe"])
                .output();
        }
    }

    *state.tunnel_running.lock().unwrap() = false;
    *state.tunnel_url.lock().unwrap() = None;
    Ok(true)
}

/// Upload tunnel URL to Azure Blob Storage with retry logic
fn upload_tunnel_url_to_azure(url: &str, config: &AppConfig) -> Result<(), String> {
    // Get SAS URL from config (persisted) or environment
    let azure_sas_url = config
        .azure_sas_url
        .clone()
        .or_else(|| std::env::var("FI_AZURE_TUNNEL_BLOB_SAS").ok())
        .unwrap_or_default();

    if azure_sas_url.is_empty() {
        println!("[FI Monitor] No Azure SAS URL configured, skipping upload");
        // Still save locally as backup
        save_tunnel_url_locally(url)?;
        return Ok(());
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp,
        "version": "1.1",
        "services": {
            "ollama": format!("{}/api", url),
            "rag": format!("{}/rag", url),
            "gateway": format!("{}/gateway/health", url)
        }
    })
    .to_string();

    // Retry with exponential backoff
    let max_retries = 3;
    let mut last_error = String::new();

    for attempt in 0..max_retries {
        if attempt > 0 {
            let delay = Duration::from_millis(500 * 2u64.pow(attempt as u32));
            println!("[FI Monitor] Retry {} in {:?}...", attempt + 1, delay);
            std::thread::sleep(delay);
        }

        println!(
            "[FI Monitor] Uploading tunnel URL to Azure (attempt {})...",
            attempt + 1
        );

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| format!("Client error: {}", e))?;

        match client
            .put(&azure_sas_url)
            .header("x-ms-blob-type", "BlockBlob")
            .header("Content-Type", "application/json")
            .body(content.clone())
            .send()
        {
            Ok(response) if response.status().is_success() => {
                println!("[FI Monitor] Tunnel URL uploaded to Azure");
                // Also save locally as backup
                let _ = save_tunnel_url_locally(url);
                return Ok(());
            }
            Ok(response) => {
                last_error = format!(
                    "HTTP {}: {}",
                    response.status(),
                    response.status().canonical_reason().unwrap_or("Unknown")
                );
                println!("[FI Monitor] Azure returned: {}", last_error);
            }
            Err(e) => {
                last_error = format!("Request failed: {}", e);
                println!("[FI Monitor] {}", last_error);
            }
        }
    }

    // All retries failed - save locally as fallback
    println!(
        "[FI Monitor] Azure upload failed after {} retries, saving locally",
        max_retries
    );
    save_tunnel_url_locally(url)?;
    Err(last_error)
}

/// Save tunnel URL locally as backup
fn save_tunnel_url_locally(url: &str) -> Result<(), String> {
    let path = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("tunnel-url.json");

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp
    });

    let json = serde_json::to_string_pretty(&content).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Tunnel URL saved locally: {:?}", path);
    Ok(())
}

/// Read the tunnel URL file content
#[tauri::command]
pub(crate) fn read_tunnel_file() -> Result<String, String> {
    let path = dirs::config_dir()
        .ok_or("Could not determine config directory")?
        .join("fi-monitor")
        .join("tunnel-url.json");

    // Verificar que el archivo existe
    if !path.exists() {
        return Err("Tunnel file not found. Start the tunnel to create it.".to_string());
    }

    // Leer contenido del archivo
    std::fs::read_to_string(&path).map_err(|e| format!("Failed to read file: {}", e))
}

/// Periodically re-upload tunnel URL to keep timestamp fresh
fn start_periodic_upload(url: String, config: AppConfig) {
    std::thread::spawn(move || {
        loop {
            // Wait 5 minutes
            std::thread::sleep(Duration::from_secs(300));

            println!("[FI Monitor] Periodic re-upload of tunnel URL...");
            if let Err(e) = upload_tunnel_url_to_azure(&url, &config) {
                println!("[FI Monitor] Periodic upload failed: {}", e);
            }
        }
    });
}

/// Check if a process with given PID is still running
fn is_process_alive(pid: u32) -> bool {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        Command::new("tasklist")
            .args(["/FI", &format!("PID eq {}", pid), "/NH"])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
            .map(|output| {
                let stdout = String::from_utf8_lossy(&output.stdout);
                stdout.contains(&pid.to_string())
            })
            .unwrap_or(false)
    }
    #[cfg(not(target_os = "windows"))]
    {
        Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
    }
}

/// Watchdog to monitor tunnel process and auto-restart if it dies
/// NOTE: This watchdog NEVER exits - it runs for the lifetime of the app
fn start_tunnel_watchdog(app: tauri::AppHandle, state: Arc<AppState>) {
    std::thread::spawn(move || {
        let mut restart_count = 0u32;
        let mut check_count = 0u32;
        println!("[FI Monitor Watchdog] Started (checking every 10s)");

        loop {
            // Check every 10 seconds (faster detection than 30s)
            std::thread::sleep(Duration::from_secs(10));
            check_count += 1;

            // Heartbeat log FIRST (every 6 checks = 60s)
            if check_count % 6 == 0 {
                println!(
                    "[FI Monitor Watchdog] Heartbeat #{}: woke up, checking state...",
                    check_count
                );
            }

            let pid_opt = *state.tunnel_process.lock().unwrap();
            let tunnel_running = *state.tunnel_running.lock().unwrap();

            // Detailed state log after reading locks
            if check_count % 6 == 0 {
                println!(
                    "[FI Monitor Watchdog] State: tunnel_running={}, pid={:?}",
                    tunnel_running, pid_opt
                );
            }

            if !tunnel_running {
                // Tunnel was manually stopped, keep watching for restart
                // DO NOT exit - watchdog must survive for app lifetime
                continue;
            }

            if let Some(pid) = pid_opt {
                if !is_process_alive(pid) {
                    restart_count += 1;
                    println!(
                        "[FI Monitor Watchdog] Tunnel process {} died! Restarting (attempt #{})...",
                        pid, restart_count
                    );

                    // Mark as not running
                    *state.tunnel_running.lock().unwrap() = false;
                    *state.tunnel_url.lock().unwrap() = None;

                    // Emit event
                    let _ = app.emit("tunnel-died", ());

                    // Wait a bit before restart
                    std::thread::sleep(Duration::from_secs(5));

                    // Trigger restart via command (this is async, so spawn it)
                    let app_clone = app.clone();
                    let state_clone = state.clone();
                    let attempt = restart_count;
                    tauri::async_runtime::spawn(async move {
                        // Re-check Ollama before restart
                        if check_ollama().await {
                            // Watchdog ALWAYS restarts cloudflared tunnel (not local)
                            // porque solo cloudflared tiene proceso que puede morir
                            match start_tunnel_cloudflared_internal(app_clone.clone(), state_clone)
                                .await
                            {
                                Ok(_) => println!(
                                    "[FI Monitor Watchdog] Tunnel restarted (attempt #{})",
                                    attempt
                                ),
                                Err(e) => {
                                    println!(
                                        "[FI Monitor Watchdog] Failed to restart (attempt #{}): {}",
                                        attempt, e
                                    )
                                }
                            }
                        } else {
                            println!(
                                "[FI Monitor Watchdog] Ollama not running, cannot restart tunnel (attempt #{})",
                                attempt
                            );
                        }
                    });

                    // DO NOT exit - continue monitoring
                    // Watchdog must survive for app lifetime to handle future crashes
                    continue;
                }
            }
        }
    });
}

/// Start local tunnel (localhost directo, sin cloudflared)
/// Usado en auto-start para modo rapido/simple
pub(crate) fn start_tunnel_local(state: Arc<AppState>) -> Result<String, String> {
    println!("[FI Monitor] Starting local tunnel (no cloudflared)...");

    // 1. Obtener puerto configurado (default: 11400 = Gateway)
    let tunnel_port = {
        let config = state.config.lock().unwrap();
        config.get_tunnel_port()
    };

    // 2. TUNNEL FICTICIO: Usar localhost directo (NO cloudflared)
    let tunnel_url = format!("http://localhost:{}", tunnel_port);
    println!("[FI Monitor] Local tunnel (ficticio): {}", tunnel_url);

    // 3. Guardar al JSON local
    save_tunnel_url_locally(&tunnel_url)?;
    println!("[FI Monitor] Saved to: ~/.config/fi-monitor/tunnel-url.json");

    // 4. Actualizar state
    *state.tunnel_url.lock().unwrap() = Some(tunnel_url.clone());
    *state.tunnel_running.lock().unwrap() = true;
    *state.tunnel_mode.lock().unwrap() = TunnelMode::Local;

    // 5. Actualizar config con last_tunnel_url
    {
        let mut cfg = state.config.lock().unwrap();
        cfg.last_tunnel_url = Some(tunnel_url.clone());
        let _ = save_config(&cfg);
    }

    // 6. Re-upload periodico (mantiene timestamp fresco cada 5 min)
    let config = state.config.lock().unwrap().clone();
    start_periodic_upload(tunnel_url.clone(), config);

    println!("[FI Monitor] Local tunnel ready");
    Ok(tunnel_url)
}

/// Internal function to start cloudflared tunnel (used by manual command and watchdog)
async fn start_tunnel_cloudflared_internal(
    app: tauri::AppHandle,
    state: Arc<AppState>,
) -> Result<String, String> {
    if !check_ollama().await {
        return Err("Ollama is not running".to_string());
    }
    if *state.tunnel_running.lock().unwrap() {
        if let Some(url) = state.tunnel_url.lock().unwrap().clone() {
            return Ok(url);
        }
    }

    // Leer puerto configurado
    let tunnel_port = {
        let config = state.config.lock().unwrap();
        config.get_tunnel_port()
    };

    let tunnel_url = format!("http://localhost:{}", tunnel_port);
    println!(
        "[FI Monitor] Starting Cloudflare tunnel to {}",
        tunnel_url
    );
    let cloudflared = find_cloudflared()?;

    #[cfg(target_os = "windows")]
    const CREATE_NO_WINDOW_LOCAL: u32 = 0x08000000;

    #[cfg(target_os = "windows")]
    let mut child = Command::new(&cloudflared)
        .args(["tunnel", "--url", &tunnel_url])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .creation_flags(CREATE_NO_WINDOW_LOCAL)
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;

    #[cfg(not(target_os = "windows"))]
    let mut child = Command::new(&cloudflared)
        .args(["tunnel", "--url", &tunnel_url])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;

    let pid = child.id();
    *state.tunnel_process.lock().unwrap() = Some(pid);
    *state.tunnel_running.lock().unwrap() = true;
    *state.tunnel_mode.lock().unwrap() = TunnelMode::Cloudflared;

    // Capture stderr in separate thread to find tunnel URL
    // IMPORTANT: Must .take() to move ownership to thread, otherwise stderr closes when child drops
    let stderr = child.stderr.take().expect("Failed to capture stderr");
    let state_clone = Arc::clone(&state);
    let app_clone = app.clone();
    let config = state.config.lock().unwrap().clone();

    // Move child into thread to keep it alive while reading stderr
    // Without this, child drops and stderr pipe closes before we can read URL
    std::thread::spawn(move || {
        // Keep child alive for the duration of this thread
        let _child_guard = child;
        let reader = BufReader::new(stderr);
        let url_regex = Regex::new(r"https://[a-z0-9-]+\.trycloudflare\.com")
            .expect("static regex must compile");

        for line in reader.lines().map_while(Result::ok) {
            println!("[cloudflared] {}", line);

            if let Some(url_match) = url_regex.find(&line) {
                let url = url_match.as_str().to_string();
                println!("[FI Monitor] Tunnel URL: {}", url);
                *state_clone.tunnel_url.lock().unwrap() = Some(url.clone());

                // Update config with last tunnel URL
                {
                    let mut cfg = state_clone.config.lock().unwrap();
                    cfg.last_tunnel_url = Some(url.clone());
                    let _ = save_config(&cfg);
                }

                // Emit event with URL
                let _ = app_clone.emit("tunnel-url-found", url.clone());
                let _ = app_clone.emit("tunnel-started", ());

                // Upload to Azure in background with retries
                let url_for_azure = url.clone();
                let config_for_upload = config.clone();
                std::thread::spawn(move || {
                    if let Err(e) =
                        upload_tunnel_url_to_azure(&url_for_azure, &config_for_upload)
                    {
                        println!("[FI Monitor] Azure upload failed: {}", e);
                    }
                });

                // Start periodic re-upload (every 5 minutes)
                start_periodic_upload(url.clone(), config.clone());

                // Start tunnel watchdog (auto-restart if it dies)
                // Only spawn watchdog ONCE (prevents duplicates on restart)
                let mut watchdog_lock = state_clone.watchdog_running.lock().unwrap();
                if !*watchdog_lock {
                    *watchdog_lock = true;
                    drop(watchdog_lock); // Release lock before spawning
                    start_tunnel_watchdog(app_clone.clone(), state_clone.clone());
                    println!(
                        "[FI Monitor] Tunnel watchdog spawned (will run for app lifetime)"
                    );
                } else {
                    println!(
                        "[FI Monitor] Watchdog already running (skipping duplicate spawn)"
                    );
                }

                break;
            }
        }

        // _child_guard drops here, but process continues running
        // (Rust Child has no Drop implementation - process is independent)
    });

    Ok("Tunnel starting... URL will appear when ready".to_string())
}

fn find_cloudflared() -> Result<String, String> {
    #[allow(unused_mut)] // mut needed on Windows for cfg-gated pushes
    let mut candidates = vec!["cloudflared".to_string()];

    #[cfg(target_os = "windows")]
    {
        // Use environment variables instead of hardcoded C:\ -- supports
        // Windows installed on any drive letter
        if let Ok(pf) = std::env::var("ProgramFiles") {
            candidates.push(format!("{}\\cloudflared\\cloudflared.exe", pf));
        }
        if let Ok(sd) = std::env::var("SystemDrive") {
            candidates.push(format!("{}\\cloudflared\\cloudflared.exe", sd));
        }
    }

    for path in candidates {
        if Command::new(&path).arg("--version").output().is_ok() {
            return Ok(path);
        }
    }
    Err("cloudflared not found".to_string())
}
