// Tauri commands for tunnel management.

use std::sync::Arc;

use crate::state::*;

use super::cloudflared::{start_tunnel_cloudflared_internal, stop_tunnel_internal};
use super::local::start_tunnel_local;
use super::upload::read_tunnel_file_content;

/// Start a cloudflared tunnel (remote access).
///
/// If a local tunnel is currently running, it is stopped first.
#[tauri::command]
pub(crate) async fn start_tunnel(
    app: tauri::AppHandle,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<String, String> {
    let current_mode = *state.tunnel_mode.lock().unwrap();
    if current_mode == TunnelMode::Local && *state.tunnel_running.lock().unwrap() {
        println!("[FI Monitor] Switching from local tunnel to cloudflared...");
        stop_tunnel_internal(Arc::clone(&*state))?;
    }

    start_tunnel_cloudflared_internal(app, Arc::clone(&*state)).await
}

/// Stop the active tunnel.
///
/// If the stopped tunnel was cloudflared, automatically falls back to local mode.
#[tauri::command]
pub(crate) async fn stop_tunnel(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    let mode = *state.tunnel_mode.lock().unwrap();

    stop_tunnel_internal(Arc::clone(&*state))?;

    if mode == TunnelMode::Cloudflared {
        println!("[FI Monitor] Returning to local tunnel mode...");
        start_tunnel_local(Arc::clone(&*state))?;
    }

    Ok(true)
}

/// Read the persisted tunnel URL file.
#[tauri::command]
pub(crate) fn read_tunnel_file() -> Result<String, String> {
    read_tunnel_file_content()
}
