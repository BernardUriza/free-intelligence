// FI Monitor - Ollama Tunnel Manager
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tokio::time::sleep;

// ============================================================================
// Configuration Persistence
// ============================================================================

#[derive(Serialize, Deserialize, Clone, Default)]
struct AppConfig {
    azure_sas_url: Option<String>,
    last_tunnel_url: Option<String>,
    last_upload_success: Option<String>,
}

fn get_config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("config.json")
}

fn load_config() -> AppConfig {
    let path = get_config_path();
    if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        AppConfig::default()
    }
}

fn save_config(config: &AppConfig) -> Result<(), String> {
    let path = get_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Config saved to {:?}", path);
    Ok(())
}

// ============================================================================
// App State
// ============================================================================

#[derive(Default)]
struct AppState {
    ollama_running: Mutex<bool>,
    tunnel_running: Mutex<bool>,
    tunnel_url: Mutex<Option<String>>,
    tunnel_process: Mutex<Option<u32>>,
    config: Mutex<AppConfig>,
}

#[derive(Serialize, Clone)]
struct ServiceStatus {
    ollama_running: bool,
    ollama_models: Vec<String>,
    tunnel_running: bool,
    tunnel_url: Option<String>,
    system_info: SystemInfo,
}

#[derive(Serialize, Clone, Default)]
struct SystemInfo {
    platform: String,
    hostname: String,
}

async fn check_ollama() -> bool {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap();
    client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

async fn get_ollama_models() -> Vec<String> {
    #[derive(Deserialize)]
    struct ModelsResponse { models: Vec<Model> }
    #[derive(Deserialize)]
    struct Model { name: String }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap();

    match client.get("http://localhost:11434/api/tags").send().await {
        Ok(response) => match response.json::<ModelsResponse>().await {
            Ok(r) => r.models.into_iter().map(|m| m.name).collect(),
            Err(_) => vec![],
        },
        Err(_) => vec![],
    }
}

#[tauri::command]
async fn start_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_ollama().await {
        *state.ollama_running.lock().unwrap() = true;
        return Ok(true);
    }
    println!("[FI Monitor] Starting Ollama...");
    let result = Command::new("ollama")
        .arg("serve")
        .env("OLLAMA_ORIGINS", "*")
        .env("OLLAMA_HOST", "0.0.0.0:11434")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
    match result {
        Ok(_) => {
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_ollama().await {
                    *state.ollama_running.lock().unwrap() = true;
                    println!("[FI Monitor] Ollama started");
                    return Ok(true);
                }
            }
            Err("Ollama started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start Ollama: {}", e)),
    }
}

#[tauri::command]
async fn stop_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Ollama...");
    #[cfg(target_os = "windows")]
    { let _ = Command::new("taskkill").args(["/F", "/IM", "ollama.exe"]).output(); }
    #[cfg(not(target_os = "windows"))]
    { let _ = Command::new("pkill").arg("ollama").output(); }
    *state.ollama_running.lock().unwrap() = false;
    Ok(true)
}

#[tauri::command]
async fn start_tunnel(app: tauri::AppHandle, state: tauri::State<'_, Arc<AppState>>) -> Result<String, String> {
    start_tunnel_internal(app, Arc::clone(&*state)).await
}

#[tauri::command]
async fn stop_tunnel(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping tunnel...");
    if let Some(pid) = state.tunnel_process.lock().unwrap().take() {
        #[cfg(target_os = "windows")]
        { let _ = Command::new("taskkill").args(["/F", "/PID", &pid.to_string()]).output(); }
        #[cfg(not(target_os = "windows"))]
        { let _ = Command::new("kill").arg(pid.to_string()).output(); }
    }
    #[cfg(target_os = "windows")]
    { let _ = Command::new("taskkill").args(["/F", "/IM", "cloudflared.exe"]).output(); }
    *state.tunnel_running.lock().unwrap() = false;
    *state.tunnel_url.lock().unwrap() = None;
    Ok(true)
}

/// Upload tunnel URL to Azure Blob Storage with retry logic
fn upload_tunnel_url_to_azure(url: &str, config: &AppConfig) -> Result<(), String> {
    // Get SAS URL from config (persisted) or environment
    let azure_sas_url = config.azure_sas_url.clone()
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
        "version": "1.0"
    }).to_string();
    
    // Retry with exponential backoff
    let max_retries = 3;
    let mut last_error = String::new();
    
    for attempt in 0..max_retries {
        if attempt > 0 {
            let delay = Duration::from_millis(500 * 2u64.pow(attempt as u32));
            println!("[FI Monitor] Retry {} in {:?}...", attempt + 1, delay);
            std::thread::sleep(delay);
        }
        
        println!("[FI Monitor] Uploading tunnel URL to Azure (attempt {})...", attempt + 1);
        
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
                println!("[FI Monitor] ✅ Tunnel URL uploaded to Azure");
                // Also save locally as backup
                let _ = save_tunnel_url_locally(url);
                return Ok(());
            }
            Ok(response) => {
                last_error = format!("HTTP {}: {}", response.status(), response.status().canonical_reason().unwrap_or("Unknown"));
                println!("[FI Monitor] ⚠️ Azure returned: {}", last_error);
            }
            Err(e) => {
                last_error = format!("Request failed: {}", e);
                println!("[FI Monitor] ⚠️ {}", last_error);
            }
        }
    }
    
    // All retries failed - save locally as fallback
    println!("[FI Monitor] ⚠️ Azure upload failed after {} retries, saving locally", max_retries);
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
    println!("[FI Monitor] 💾 Tunnel URL saved locally: {:?}", path);
    Ok(())
}

/// Periodically re-upload tunnel URL to keep timestamp fresh
fn start_periodic_upload(url: String, config: AppConfig) {
    std::thread::spawn(move || {
        loop {
            // Wait 5 minutes
            std::thread::sleep(Duration::from_secs(300));
            
            println!("[FI Monitor] 🔄 Periodic re-upload of tunnel URL...");
            if let Err(e) = upload_tunnel_url_to_azure(&url, &config) {
                println!("[FI Monitor] ⚠️ Periodic upload failed: {}", e);
            }
        }
    });
}

/// Check if a process with given PID is still running
fn is_process_alive(pid: u32) -> bool {
    #[cfg(target_os = "windows")]
    {
        Command::new("tasklist")
            .args(["/FI", &format!("PID eq {}", pid), "/NH"])
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
fn start_tunnel_watchdog(app: tauri::AppHandle, state: Arc<AppState>) {
    std::thread::spawn(move || {
        loop {
            // Check every 30 seconds
            std::thread::sleep(Duration::from_secs(30));

            let pid_opt = state.tunnel_process.lock().unwrap().clone();
            let tunnel_running = *state.tunnel_running.lock().unwrap();

            if !tunnel_running {
                // Tunnel was manually stopped, exit watchdog
                println!("[FI Monitor Watchdog] Tunnel stopped, exiting watchdog");
                break;
            }

            if let Some(pid) = pid_opt {
                if !is_process_alive(pid) {
                    println!("[FI Monitor Watchdog] ⚠️ Tunnel process {} died! Restarting...", pid);

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
                    tauri::async_runtime::spawn(async move {
                        // Re-check Ollama before restart
                        if check_ollama().await {
                            match start_tunnel_internal(app_clone.clone(), state_clone).await {
                                Ok(_) => println!("[FI Monitor Watchdog] ✅ Tunnel restarted"),
                                Err(e) => println!("[FI Monitor Watchdog] ❌ Failed to restart: {}", e),
                            }
                        } else {
                            println!("[FI Monitor Watchdog] ❌ Ollama not running, cannot restart tunnel");
                        }
                    });

                    // Exit this watchdog, the restart will spawn a new one
                    break;
                }
            }
        }
    });
}

/// Internal function to start tunnel (used by both command and watchdog)
async fn start_tunnel_internal(app: tauri::AppHandle, state: Arc<AppState>) -> Result<String, String> {
    if !check_ollama().await {
        return Err("Ollama is not running".to_string());
    }
    if *state.tunnel_running.lock().unwrap() {
        if let Some(url) = state.tunnel_url.lock().unwrap().clone() {
            return Ok(url);
        }
    }
    println!("[FI Monitor] Starting Cloudflare tunnel...");
    let cloudflared = find_cloudflared()?;
    let mut child = Command::new(&cloudflared)
        .args(["tunnel", "--url", "http://localhost:11434"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;

    let pid = child.id();
    *state.tunnel_process.lock().unwrap() = Some(pid);
    *state.tunnel_running.lock().unwrap() = true;

    // Capture stderr in separate thread to find tunnel URL
    let stderr = child.stderr.take().expect("Failed to capture stderr");
    let state_clone = Arc::clone(&state);
    let app_clone = app.clone();
    let config = state.config.lock().unwrap().clone();

    std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        let url_regex = Regex::new(r"https://[a-z0-9-]+\.trycloudflare\.com").unwrap();

        for line in reader.lines().map_while(Result::ok) {
            println!("[cloudflared] {}", line);

            if let Some(url_match) = url_regex.find(&line) {
                let url = url_match.as_str().to_string();
                println!("[FI Monitor] ✅ Tunnel URL: {}", url);
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
                    if let Err(e) = upload_tunnel_url_to_azure(&url_for_azure, &config_for_upload) {
                        println!("[FI Monitor] ⚠️ Azure upload failed: {}", e);
                    }
                });

                // Start periodic re-upload (every 5 minutes)
                start_periodic_upload(url.clone(), config.clone());

                // Start tunnel watchdog (auto-restart if it dies)
                start_tunnel_watchdog(app_clone.clone(), state_clone.clone());

                break;
            }
        }
    });

    Ok("Tunnel starting... URL will appear when ready".to_string())
}

fn find_cloudflared() -> Result<String, String> {
    let candidates = vec![
        "cloudflared".to_string(),
        "C:\\cloudflared\\cloudflared.exe".to_string(),
        "C:\\Program Files\\cloudflared\\cloudflared.exe".to_string(),
    ];
    for path in candidates {
        if Command::new(&path).arg("--version").output().is_ok() {
            return Ok(path);
        }
    }
    Err("cloudflared not found".to_string())
}

#[tauri::command]
async fn get_status(state: tauri::State<'_, Arc<AppState>>) -> Result<ServiceStatus, String> {
    let ollama_running = check_ollama().await;
    let models = if ollama_running { get_ollama_models().await } else { vec![] };
    *state.ollama_running.lock().unwrap() = ollama_running;
    Ok(ServiceStatus {
        ollama_running,
        ollama_models: models,
        tunnel_running: *state.tunnel_running.lock().unwrap(),
        tunnel_url: state.tunnel_url.lock().unwrap().clone(),
        system_info: SystemInfo {
            platform: std::env::consts::OS.to_string(),
            hostname: gethostname::gethostname().to_string_lossy().to_string(),
        },
    })
}

#[tauri::command]
async fn test_ollama() -> Result<TestResult, String> {
    use std::time::Instant;
    if !check_ollama().await {
        return Err("Ollama no está ejecutándose".to_string());
    }
    let questions = vec![
        ("math", "¿Cuál es la raíz cuadrada de 144? Responde solo el número."),
        ("anatomy", "Explica brevemente qué es el hígado y su función principal."),
        ("math", "¿Cuál es la raíz cuadrada de 256? Responde solo el número."),
        ("anatomy", "Explica brevemente qué es el corazón y su función principal."),
        ("math", "¿Cuál es la raíz cuadrada de 625? Responde solo el número."),
        ("anatomy", "Explica brevemente qué son los pulmones y su función."),
    ];
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
    let idx = (now % questions.len() as u64) as usize;
    let (category, prompt) = questions[idx];
    println!("[FI Monitor] Testing: {}", prompt);
    let start = Instant::now();
    let client = reqwest::Client::builder().timeout(Duration::from_secs(60)).build().unwrap();
    #[derive(Serialize)]
    struct Req { model: String, prompt: String, stream: bool }
    #[derive(Deserialize)]
    struct Res { response: String }
    let request = Req { model: "qwen3:1.7b".to_string(), prompt: prompt.to_string(), stream: false };
    let response = client.post("http://localhost:11434/api/generate").json(&request).send().await
        .map_err(|e| format!("Error: {}", e))?;
    let res: Res = response.json().await.map_err(|e| format!("Parse error: {}", e))?;
    let elapsed_ms = start.elapsed().as_millis() as u64;
    println!("[FI Monitor] Response in {}ms", elapsed_ms);
    Ok(TestResult { category: category.to_string(), question: prompt.to_string(), answer: res.response.trim().to_string(), elapsed_ms, timestamp: chrono::Utc::now().to_rfc3339() })
}

#[derive(Serialize, Clone)]
struct TestResult { category: String, question: String, answer: String, elapsed_ms: u64, timestamp: String }

#[tauri::command]
async fn is_autostart_enabled(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch().is_enabled().map_err(|e: tauri_plugin_autostart::Error| e.to_string())
}

#[tauri::command]
async fn enable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch().enable().map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}

#[tauri::command]
async fn disable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch().disable().map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}

// ============================================================================
// Config Commands
// ============================================================================

#[tauri::command]
async fn set_azure_sas_url(state: tauri::State<'_, Arc<AppState>>, sas_url: String) -> Result<bool, String> {
    let mut config = state.config.lock().unwrap();
    config.azure_sas_url = Some(sas_url);
    save_config(&config)?;
    println!("[FI Monitor] Azure SAS URL configured and saved");
    Ok(true)
}

#[tauri::command]
async fn get_azure_sas_url(state: tauri::State<'_, Arc<AppState>>) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.azure_sas_url.clone())
}

#[tauri::command]
async fn get_last_tunnel_url(state: tauri::State<'_, Arc<AppState>>) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.last_tunnel_url.clone())
}

fn main() {
    // Load persisted config
    let config = load_config();
    println!("[FI Monitor] Config loaded from {:?}", get_config_path());
    if config.azure_sas_url.is_some() {
        println!("[FI Monitor] Azure SAS URL: configured ✓");
    }
    if let Some(ref url) = config.last_tunnel_url {
        println!("[FI Monitor] Last tunnel URL: {}", url);
    }
    
    let state = Arc::new(AppState {
        config: Mutex::new(config),
        ..Default::default()
    });
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, Some(vec!["--minimized"])))
        .manage(state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_clone = state.clone();
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "Show", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("FI Monitor")
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "quit" => app.exit(0),
                    "show" => { if let Some(w) = app.get_webview_window("main") { let _ = w.show(); let _ = w.set_focus(); } }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                        if let Some(w) = tray.app_handle().get_webview_window("main") { let _ = w.show(); let _ = w.set_focus(); }
                    }
                })
                .build(app)?;
            
            // Intercept close to minimize to tray instead of quitting
            if let Some(window) = app.get_webview_window("main") {
                let window_clone = window.clone();
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = window_clone.hide();
                        println!("[FI Monitor] Window minimized to tray");
                    }
                });
            }
            
            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking services (with startup retry)...");
                // Retry logic for startup - Ollama might still be booting
                let mut attempts = 0;
                let max_attempts = 20; // 20 attempts × 1.5s = 30s max
                while attempts < max_attempts {
                    if check_ollama().await {
                        *state_clone.ollama_running.lock().unwrap() = true;
                        println!("[FI Monitor] ✅ Ollama running (attempt {})", attempts + 1);
                        let _ = app_handle.emit("services-checked", ());

                        // Auto-start tunnel if Ollama is running
                        println!("[FI Monitor] Auto-starting tunnel...");
                        match start_tunnel_internal(app_handle.clone(), state_clone.clone()).await {
                            Ok(_) => println!("[FI Monitor] ✅ Tunnel auto-started"),
                            Err(e) => println!("[FI Monitor] ⚠️ Failed to auto-start tunnel: {}", e),
                        }
                        return;
                    }
                    attempts += 1;
                    if attempts < max_attempts {
                        println!("[FI Monitor] ⏳ Ollama not ready, retrying ({}/{})...", attempts, max_attempts);
                        sleep(Duration::from_millis(1500)).await;
                    }
                }
                println!("[FI Monitor] ⚠️ Ollama not found after {} attempts", max_attempts);
                let _ = app_handle.emit("services-checked", ());
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![start_ollama, stop_ollama, start_tunnel, stop_tunnel, get_status, test_ollama, is_autostart_enabled, enable_autostart, disable_autostart, set_azure_sas_url, get_azure_sas_url, get_last_tunnel_url])
        .run(tauri::generate_context!())
        .expect("error running FI Monitor");
}
