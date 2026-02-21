// Aurity Desktop — Main Entry Point
//
// Module structure (SRP):
//   constants.rs  — App-level configuration (ports, timeouts, durations)
//   errors.rs     — AppError enum + From impls
//   backend.rs    — BackendState, port allocation, health checks, sidecar lifecycle
//   ollama.rs     — Ollama health checks, edge infrastructure management
//   autostart.rs  — Windows registry Run key management
//   wizard.rs     — Wizard state persistence, first-run status, Python verification
//   config.rs     — First-run bootstrap, data directory, atomic file writes
//   window.rs     — Splash/main window transition, status events, deep links

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod auth;
mod autostart;
mod backend;
mod config;
mod constants;
mod errors;
mod fi_monitor;
mod license;
mod ollama;
mod templates;
mod window;
mod wizard;
mod wsl;

use std::sync::Arc;

use log::{info, warn};
use tauri::Emitter;

use auth::AuthState;
use backend::BackendState;

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let backend_state = Arc::new(BackendState::new());
    let auth_state = AuthState::default();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(backend_state.clone())
        .manage(auth_state)
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state = backend_state.clone();

            window::register_deep_links(app);

            window::emit_status(&app_handle, "Verificando configuración...");
            match config::bootstrap_config(&app_handle) {
                Ok(true) => {
                    info!("First run - config bootstrapped");
                    let _ = app_handle.emit("first-run-detected", ());
                }
                Ok(false) => {
                    info!("Config already exists");
                }
                Err(e) => {
                    let err_str = e.to_string();
                    if err_str.contains("permission")
                        || err_str.contains("denied")
                        || err_str.contains("access")
                    {
                        warn!("Permission error bootstrapping config: {}", e);
                        window::emit_status(&app_handle, "Error de permisos al crear la configuración. Verifica que tienes permisos de escritura en tu carpeta de usuario.");
                    } else {
                        warn!("Failed to bootstrap config: {}", e);
                    }
                }
            }

            tauri::async_runtime::spawn(backend::spawn_backend(app_handle, state));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Backend
            backend::get_backend_url,
            backend::get_backend_status,
            // Ollama
            ollama::check_ollama_status,
            ollama::ensure_edge_infrastructure,
            // Wizard & first-run
            wizard::check_first_run_status,
            wizard::get_wizard_state,
            wizard::mark_desktop_setup_complete,
            wizard::reset_wizard_state,
            // Windows autostart
            autostart::setup_windows_autostart,
            autostart::remove_windows_autostart,
            autostart::check_windows_autostart,
            // Python verification
            wizard::check_python_installation,
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
