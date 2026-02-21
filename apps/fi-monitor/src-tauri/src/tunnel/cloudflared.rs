// Cloudflared process lifecycle — start, stop, and binary discovery.

use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio};
use std::sync::Arc;

use regex::Regex;
use tauri::Emitter;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

use crate::config::save_config;
use crate::ollama::check_ollama;
use crate::state::*;

use super::upload::{start_periodic_upload, upload_tunnel_url_to_azure};
use super::watchdog::start_tunnel_watchdog;

/// Stop the active tunnel process without restarting local mode.
pub(super) fn stop_tunnel_internal(state: Arc<AppState>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping tunnel...");

    let mode = *state.tunnel_mode.lock().unwrap();

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

/// Start a cloudflared tunnel pointing at the configured port.
///
/// Called by the manual `start_tunnel` command and by the watchdog on restart.
pub(super) async fn start_tunnel_cloudflared_internal(
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

    let tunnel_port = {
        let config = state.config.lock().unwrap();
        config.get_tunnel_port()
    };

    let tunnel_url = format!("http://localhost:{}", tunnel_port);
    println!("[FI Monitor] Starting Cloudflare tunnel to {}", tunnel_url);
    let cloudflared = find_cloudflared()?;

    let mut child = spawn_cloudflared(&cloudflared, &tunnel_url)?;

    let pid = child.id();
    *state.tunnel_process.lock().unwrap() = Some(pid);
    *state.tunnel_running.lock().unwrap() = true;
    *state.tunnel_mode.lock().unwrap() = TunnelMode::Cloudflared;

    // Capture stderr in a separate thread to find the tunnel URL.
    // Must .take() to move ownership; otherwise stderr closes when child drops.
    let stderr = child.stderr.take().expect("Failed to capture stderr");
    let state_clone = Arc::clone(&state);
    let app_clone = app.clone();
    let config = state.config.lock().unwrap().clone();

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

                {
                    let mut cfg = state_clone.config.lock().unwrap();
                    cfg.last_tunnel_url = Some(url.clone());
                    let _ = save_config(&cfg);
                }

                let _ = app_clone.emit("tunnel-url-found", url.clone());
                let _ = app_clone.emit("tunnel-started", ());

                // Azure upload in background
                let url_for_azure = url.clone();
                let config_for_upload = config.clone();
                std::thread::spawn(move || {
                    if let Err(e) =
                        upload_tunnel_url_to_azure(&url_for_azure, &config_for_upload)
                    {
                        println!("[FI Monitor] Azure upload failed: {}", e);
                    }
                });

                start_periodic_upload(url.clone(), config.clone());

                // Spawn watchdog once (prevents duplicates on restart)
                let mut watchdog_lock = state_clone.watchdog_running.lock().unwrap();
                if !*watchdog_lock {
                    *watchdog_lock = true;
                    drop(watchdog_lock);
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
    });

    Ok("Tunnel starting... URL will appear when ready".to_string())
}

/// Spawn the cloudflared child process with platform-specific flags.
fn spawn_cloudflared(
    cloudflared: &str,
    tunnel_url: &str,
) -> Result<std::process::Child, String> {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        Command::new(cloudflared)
            .args(["tunnel", "--url", tunnel_url])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|e| format!("Failed to start cloudflared: {}", e))
    }
    #[cfg(not(target_os = "windows"))]
    {
        Command::new(cloudflared)
            .args(["tunnel", "--url", tunnel_url])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start cloudflared: {}", e))
    }
}

/// Locate the cloudflared binary on the system.
fn find_cloudflared() -> Result<String, String> {
    #[allow(unused_mut)]
    let mut candidates = vec!["cloudflared".to_string()];

    #[cfg(target_os = "windows")]
    {
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
