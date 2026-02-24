// Local tunnel mode — localhost-only, no cloudflared.

use std::sync::Arc;

use crate::config::save_config;
use crate::state::*;

use super::upload::{save_tunnel_url_locally, start_periodic_upload};

/// Start local tunnel (localhost directo, sin cloudflared).
///
/// Used during auto-start for a fast/simple mode that points directly
/// at the configured tunnel port without spawning cloudflared.
pub(crate) fn start_tunnel_local(state: Arc<AppState>) -> Result<String, String> {
    println!("[FI Monitor] Starting local tunnel (no cloudflared)...");

    let tunnel_port = {
        let config = state.config.lock().unwrap();
        config.get_tunnel_port()
    };

    let tunnel_url = format!("http://localhost:{}", tunnel_port);
    println!("[FI Monitor] Local tunnel (ficticio): {}", tunnel_url);

    save_tunnel_url_locally(&tunnel_url)?;
    println!("[FI Monitor] Saved to: ~/.config/fi-monitor/tunnel-url.json");

    *state.tunnel_url.lock().unwrap() = Some(tunnel_url.clone());
    *state.tunnel_running.lock().unwrap() = true;
    *state.tunnel_mode.lock().unwrap() = TunnelMode::Local;

    {
        let mut cfg = state.config.lock().unwrap();
        cfg.last_tunnel_url = Some(tunnel_url.clone());
        let _ = save_config(&cfg);
    }

    let config = state.config.lock().unwrap().clone();
    start_periodic_upload(tunnel_url.clone(), config);

    println!("[FI Monitor] Local tunnel ready");
    Ok(tunnel_url)
}
