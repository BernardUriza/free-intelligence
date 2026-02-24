// Generic sidecar launcher — DRY helper for starting fi-backend sidecars.

use std::future::Future;
use std::sync::Mutex;
use std::time::Duration;

use tauri_plugin_shell::ShellExt;
use tokio::time::sleep;

/// Launch an `fi-backend` sidecar with the given args, poll `health_check`
/// until it succeeds (up to 15 s), and update the shared state flags.
pub(super) async fn start_sidecar<F, Fut>(
    app_handle: &tauri::AppHandle,
    name: &str,
    args: &[&str],
    health_check: F,
    running_flag: &Mutex<bool>,
    process_pid: &Mutex<Option<u32>>,
) -> Result<bool, String>
where
    F: Fn() -> Fut,
    Fut: Future<Output = bool>,
{
    if health_check().await {
        *running_flag.lock().unwrap() = true;
        return Ok(true);
    }

    println!("[FI Monitor] Starting {} via sidecar...", name);

    let shell = app_handle.shell();
    let sidecar_cmd = shell
        .sidecar("fi-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?;

    let (mut rx, child) = sidecar_cmd
        .args(args)
        .spawn()
        .map_err(|e| format!("Failed to spawn {} sidecar: {}", name, e))?;

    let pid = child.pid();
    *process_pid.lock().unwrap() = Some(pid);

    // Stream stdout/stderr in a background task
    let label = format!("fi-backend/{}", name.to_lowercase());
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                    println!("[{}] {}", label, String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    eprintln!("[{}] {}", label, String::from_utf8_lossy(&line));
                }
                tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                    println!("[{}] Terminated: {:?}", label, status);
                    break;
                }
                _ => {}
            }
        }
    });

    // Poll health check (30 × 500 ms = 15 s max)
    for _ in 0..30 {
        sleep(Duration::from_millis(500)).await;
        if health_check().await {
            *running_flag.lock().unwrap() = true;
            println!("[FI Monitor] {} started (PID: {})", name, pid);
            return Ok(true);
        }
    }

    Err(format!("{} started but not responding", name))
}
