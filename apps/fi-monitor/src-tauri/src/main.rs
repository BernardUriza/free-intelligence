// FI Monitor - Ollama Tunnel Manager
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
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

#[derive(Default)]
struct AppState {
    ollama_running: Mutex<bool>,
    tunnel_running: Mutex<bool>,
    tunnel_url: Mutex<Option<String>>,
    tunnel_process: Mutex<Option<u32>>,
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
    let child = Command::new(&cloudflared)
        .args(["tunnel", "--url", "http://localhost:11434"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start cloudflared: {}", e))?;
    let pid = child.id();
    *state.tunnel_process.lock().unwrap() = Some(pid);
    *state.tunnel_running.lock().unwrap() = true;
    let app_clone = app.clone();
    tauri::async_runtime::spawn(async move {
        sleep(Duration::from_secs(5)).await;
        let _ = app_clone.emit("tunnel-started", ());
    });
    Ok("Tunnel starting...".to_string())
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

fn main() {
    let state = Arc::new(AppState::default());
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
            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking services...");
                if check_ollama().await {
                    *state_clone.ollama_running.lock().unwrap() = true;
                    println!("[FI Monitor] Ollama running");
                }
                let _ = app_handle.emit("services-checked", ());
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![start_ollama, stop_ollama, start_tunnel, stop_tunnel, get_status, test_ollama, is_autostart_enabled, enable_autostart, disable_autostart])
        .run(tauri::generate_context!())
        .expect("error running FI Monitor");
}
