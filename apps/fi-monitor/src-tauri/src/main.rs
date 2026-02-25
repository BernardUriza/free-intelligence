// FI Monitor - Ollama Tunnel Manager
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod autostart;
mod benchmarks;
mod config;
mod ollama;
mod ollama_installer;
mod python_installer;
mod services;
mod setup_store;
mod state;
mod testing;
mod tunnel;
mod utils;

use std::sync::{Arc, Mutex};

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_updater::UpdaterExt;
use tokio::time::sleep;

use crate::config::{check_single_instance, cleanup_lock, get_config_path, load_config};
use crate::state::AppState;

/// Port where the localhost plugin serves the frontend (for browser access).
static LOCALHOST_PORT: std::sync::OnceLock<u16> = std::sync::OnceLock::new();

/// Tauri command: get the localhost URL for browser access.
#[tauri::command]
fn get_browser_url() -> Option<String> {
    LOCALHOST_PORT.get().map(|port| format!("http://localhost:{}", port))
}

fn main() {
    // Check for single instance FIRST (fail hard if already running)
    check_single_instance();

    // Setup cleanup on panic
    std::panic::set_hook(Box::new(move |panic_info| {
        cleanup_lock();
        eprintln!("FI Monitor panicked: {:?}", panic_info);
    }));

    // Load persisted config
    let config = load_config();
    println!("[FI Monitor] Config loaded from {:?}", get_config_path());
    if config.azure_sas_url.is_some() {
        println!("[FI Monitor] Azure SAS URL: configured");
    }
    if let Some(ref url) = config.last_tunnel_url {
        println!("[FI Monitor] Last tunnel URL: {}", url);
    }

    // Pick a port for the localhost plugin (browser access)
    let port = portpicker::pick_unused_port().unwrap_or(1430);
    LOCALHOST_PORT.set(port).ok();
    println!("[FI Monitor] Browser URL: http://localhost:{}", port);

    let state = Arc::new(AppState {
        config: Mutex::new(config),
        ..Default::default()
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_localhost::Builder::new(port).build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_clone = state.clone();

            // Setup system tray with Rust TrayIconBuilder
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "Show", true, None::<&str>)?;
            let browser = MenuItem::with_id(app, "browser", "Open in Browser", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &browser, &quit])?;
            let tray_builder = TrayIconBuilder::new();
            let tray_builder = match app.default_window_icon() {
                Some(icon) => tray_builder.icon(icon.clone()),
                None => tray_builder,
            };
            let _tray = tray_builder
                .menu(&menu)
                .tooltip("FI Monitor")
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "quit" => app.exit(0),
                    "show" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "browser" => {
                        if let Some(port) = LOCALHOST_PORT.get() {
                            let url = format!("http://localhost:{}", port);
                            let _ = app.shell().open(&url, None::<tauri_plugin_shell::open::Program>);
                        }
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        if let Some(w) = tray.app_handle().get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
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

            // Check for updates in background
            let app_for_update = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking for updates...");
                match app_for_update.updater() {
                    Ok(updater) => match updater.check().await {
                        Ok(Some(update)) => {
                            println!(
                                "[FI Monitor] Update available: {} -> {}",
                                update.current_version, update.version
                            );
                            println!("[FI Monitor] Downloading and installing update...");

                            match update.download_and_install(|_, _| {}, || {}).await {
                                Ok(_) => {
                                    println!("[FI Monitor] Update installed successfully! Restart required.");
                                }
                                Err(e) => {
                                    println!("[FI Monitor] Failed to install update: {}", e);
                                }
                            }
                        }
                        Ok(None) => {
                            println!("[FI Monitor] Already up to date");
                        }
                        Err(e) => {
                            println!("[FI Monitor] Failed to check for updates: {}", e);
                        }
                    },
                    Err(e) => {
                        println!("[FI Monitor] Failed to initialize updater: {}", e);
                    }
                }
            });

            tauri::async_runtime::spawn(async move {
                println!("[FI Monitor] Checking services (with startup retry)...");
                // Retry logic for startup - Ollama might still be booting
                let mut attempts = 0;
                let max_attempts = 20; // 20 attempts x 1.5s = 30s max
                while attempts < max_attempts {
                    if ollama::check_ollama().await {
                        *state_clone.ollama_running.lock().unwrap() = true;
                        println!(
                            "[FI Monitor] Ollama running (attempt {})",
                            attempts + 1
                        );

                        // Phase 3: Auto-start RAG Service (GPU embeddings)
                        println!("[FI Monitor] Auto-starting RAG Service...");
                        match services::start_rag_service_internal(
                            &app_handle,
                            state_clone.clone(),
                        )
                        .await
                        {
                            Ok(_) => println!("[FI Monitor] RAG Service auto-started"),
                            Err(e) => {
                                println!("[FI Monitor] RAG Service failed to auto-start: {}", e)
                            }
                        }

                        // Phase 3: Auto-start Gateway (HTTP router)
                        println!("[FI Monitor] Auto-starting Gateway...");
                        match services::start_gateway_internal(&app_handle, state_clone.clone())
                            .await
                        {
                            Ok(_) => println!("[FI Monitor] Gateway auto-started"),
                            Err(e) => {
                                println!("[FI Monitor] Gateway failed to auto-start: {}", e)
                            }
                        }

                        let _ = app_handle.emit("services-checked", ());

                        // Auto-start LOCAL tunnel (localhost directo, sin cloudflared)
                        println!("[FI Monitor] Auto-starting local tunnel...");
                        match tunnel::start_tunnel_local(state_clone.clone()) {
                            Ok(url) => {
                                println!("[FI Monitor] Local tunnel ready: {}", url);
                                let _ = app_handle.emit("tunnel-url-found", url.clone());
                                let _ = app_handle.emit("tunnel-started", ());
                            }
                            Err(e) => {
                                println!("[FI Monitor] Failed to start local tunnel: {}", e);
                            }
                        }
                        return;
                    }
                    attempts += 1;
                    if attempts < max_attempts {
                        println!(
                            "[FI Monitor] Ollama not ready, retrying ({}/{})...",
                            attempts, max_attempts
                        );
                        sleep(std::time::Duration::from_millis(1500)).await;
                    }
                }
                println!(
                    "[FI Monitor] Ollama not found after {} attempts",
                    max_attempts
                );
                let _ = app_handle.emit("services-checked", ());
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ollama::start_ollama,
            ollama::stop_ollama,
            services::start_rag_service,
            services::stop_rag_service,
            services::get_rag_stats,
            services::start_gateway,
            services::stop_gateway,
            tunnel::start_tunnel,
            tunnel::stop_tunnel,
            testing::get_status,
            testing::test_ollama,
            testing::test_llm_health,
            autostart::is_autostart_enabled,
            autostart::enable_autostart,
            autostart::disable_autostart,
            config::set_azure_sas_url,
            config::get_azure_sas_url,
            benchmarks::benchmark_rag_service,
            benchmarks::benchmark_ollama,
            benchmarks::benchmark_gateway,
            benchmarks::benchmark_all,
            benchmarks::get_benchmark_history,
            config::get_last_tunnel_url,
            config::set_tunnel_port,
            config::get_tunnel_port,
            tunnel::read_tunnel_file,
            // Model Management
            ollama::list_ollama_models_detailed,
            ollama::pull_ollama_model,
            ollama::delete_ollama_model,
            // Environment Variables
            ollama::get_env_vars,
            ollama::set_env_vars,
            ollama_installer::check_ollama_installed,
            ollama_installer::install_ollama_silent,
            ollama_installer::download_and_install_ollama,
            python_installer::check_python_installed,
            python_installer::install_python_silent,
            python_installer::download_and_install_python,
            setup_store::get_setup_state,
            setup_store::update_setup_state,
            setup_store::mark_setup_completed,
            setup_store::mark_setup_skipped,
            get_browser_url,
        ])
        .run(tauri::generate_context!())
        .expect("error running FI Monitor");

    // Cleanup on normal exit
    cleanup_lock();
}
