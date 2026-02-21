// Tunnel watchdog — monitors cloudflared process and auto-restarts on crash.

use std::sync::Arc;
use std::time::Duration;

use tauri::Emitter;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

use crate::ollama::check_ollama;
use crate::state::AppState;

use super::cloudflared::start_tunnel_cloudflared_internal;

/// Check if a process with the given PID is still running.
fn is_process_alive(pid: u32) -> bool {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        std::process::Command::new("tasklist")
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
        std::process::Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
    }
}

/// Watchdog to monitor tunnel process and auto-restart if it dies.
///
/// This watchdog **never** exits — it runs for the lifetime of the app.
/// If the tunnel process disappears, it waits 5 s, re-checks Ollama, and
/// spawns a new cloudflared tunnel via [`start_tunnel_cloudflared_internal`].
pub(super) fn start_tunnel_watchdog(app: tauri::AppHandle, state: Arc<AppState>) {
    std::thread::spawn(move || {
        let mut restart_count = 0u32;
        let mut check_count = 0u32;
        println!("[FI Monitor Watchdog] Started (checking every 10s)");

        loop {
            std::thread::sleep(Duration::from_secs(10));
            check_count += 1;

            // Heartbeat log every 60 s
            if check_count % 6 == 0 {
                println!(
                    "[FI Monitor Watchdog] Heartbeat #{}: woke up, checking state...",
                    check_count
                );
            }

            let pid_opt = *state.tunnel_process.lock().unwrap();
            let tunnel_running = *state.tunnel_running.lock().unwrap();

            if check_count % 6 == 0 {
                println!(
                    "[FI Monitor Watchdog] State: tunnel_running={}, pid={:?}",
                    tunnel_running, pid_opt
                );
            }

            if !tunnel_running {
                continue;
            }

            if let Some(pid) = pid_opt {
                if !is_process_alive(pid) {
                    restart_count += 1;
                    println!(
                        "[FI Monitor Watchdog] Tunnel process {} died! Restarting (attempt #{})...",
                        pid, restart_count
                    );

                    *state.tunnel_running.lock().unwrap() = false;
                    *state.tunnel_url.lock().unwrap() = None;

                    let _ = app.emit("tunnel-died", ());

                    std::thread::sleep(Duration::from_secs(5));

                    let app_clone = app.clone();
                    let state_clone = state.clone();
                    let attempt = restart_count;
                    tauri::async_runtime::spawn(async move {
                        if check_ollama().await {
                            match start_tunnel_cloudflared_internal(app_clone.clone(), state_clone)
                                .await
                            {
                                Ok(_) => println!(
                                    "[FI Monitor Watchdog] Tunnel restarted (attempt #{})",
                                    attempt
                                ),
                                Err(e) => println!(
                                    "[FI Monitor Watchdog] Failed to restart (attempt #{}): {}",
                                    attempt, e
                                ),
                            }
                        } else {
                            println!(
                                "[FI Monitor Watchdog] Ollama not running, cannot restart tunnel (attempt #{})",
                                attempt
                            );
                        }
                    });

                    continue;
                }
            }
        }
    });
}
