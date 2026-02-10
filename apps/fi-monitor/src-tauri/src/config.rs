use crate::state::*;
use std::path::PathBuf;
use std::sync::Arc;

pub(crate) fn get_config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("config.json")
}

pub(crate) fn load_config() -> AppConfig {
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

pub(crate) fn save_config(config: &AppConfig) -> Result<(), String> {
    let path = get_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Config saved to {:?}", path);
    Ok(())
}

pub(crate) fn get_app_lock_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("app.lock")
}

pub(crate) fn check_single_instance() {
    let lock_path = get_app_lock_path();

    if lock_path.exists() {
        // Read existing PID
        if let Ok(pid_str) = std::fs::read_to_string(&lock_path) {
            if let Ok(pid) = pid_str.trim().parse::<u32>() {
                // Check if process is still running
                #[cfg(target_os = "windows")]
                let running = {
                    use std::process::Command;
                    Command::new("tasklist")
                        .args(["/FI", &format!("PID eq {}", pid)])
                        .output()
                        .map(|output| {
                            String::from_utf8_lossy(&output.stdout).contains(&pid.to_string())
                        })
                        .unwrap_or(false)
                };

                #[cfg(not(target_os = "windows"))]
                let running = {
                    use std::process::Command;
                    Command::new("kill")
                        .args(["-0", &pid.to_string()])
                        .status()
                        .map(|status| status.success())
                        .unwrap_or(false)
                };

                if running {
                    eprintln!(
                        "\n ERROR: FI Monitor ya esta corriendo (PID: {})",
                        pid
                    );
                    eprintln!("   Cierra la instancia actual antes de lanzar otra.\n");
                    eprintln!("   Comando para cerrar:");
                    #[cfg(target_os = "windows")]
                    eprintln!("   taskkill /F /PID {}\n", pid);
                    #[cfg(not(target_os = "windows"))]
                    eprintln!("   kill {}\n", pid);
                    std::process::exit(1);
                }
            }
        }
        // Stale lockfile, remove it
        let _ = std::fs::remove_file(&lock_path);
    }

    // Create lockfile with current PID
    let current_pid = std::process::id();
    if let Some(parent) = lock_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    std::fs::write(&lock_path, current_pid.to_string()).expect("Failed to create lockfile");

    println!(
        "[FI Monitor] Single instance check passed (PID: {})",
        current_pid
    );
}

pub(crate) fn cleanup_lock() {
    let lock_path = get_app_lock_path();
    if lock_path.exists() {
        let _ = std::fs::remove_file(&lock_path);
    }
}

pub(crate) async fn is_port_in_use(port: u16) -> bool {
    use std::net::TcpListener;
    TcpListener::bind(("127.0.0.1", port)).is_err()
}

#[tauri::command]
pub(crate) async fn set_azure_sas_url(
    state: tauri::State<'_, Arc<AppState>>,
    sas_url: String,
) -> Result<bool, String> {
    let mut config = state.config.lock().unwrap();
    config.azure_sas_url = Some(sas_url);
    save_config(&config)?;
    println!("[FI Monitor] Azure SAS URL configured and saved");
    Ok(true)
}

#[tauri::command]
pub(crate) async fn get_azure_sas_url(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.azure_sas_url.clone())
}

#[tauri::command]
pub(crate) async fn get_last_tunnel_url(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Option<String>, String> {
    let config = state.config.lock().unwrap();
    Ok(config.last_tunnel_url.clone())
}

#[tauri::command]
pub(crate) async fn set_tunnel_port(
    state: tauri::State<'_, Arc<AppState>>,
    port: u16,
) -> Result<(), String> {
    // Validacion
    if port < 1024 {
        return Err("Port must be >= 1024 (system ports reserved)".to_string());
    }

    // Tunnel debe estar detenido
    if *state.tunnel_running.lock().unwrap() {
        return Err("Stop tunnel before changing port".to_string());
    }

    // Verificar puerto no en uso
    if is_port_in_use(port).await {
        return Err(format!("Port {} already in use", port));
    }

    // Guardar config
    let mut config = state.config.lock().unwrap();
    config.tunnel_port = Some(port);
    save_config(&config)?;

    println!("[FI Monitor] Tunnel port updated to {}", port);
    Ok(())
}

#[tauri::command]
pub(crate) async fn get_tunnel_port(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<u16, String> {
    let config = state.config.lock().unwrap();
    Ok(config.get_tunnel_port())
}
