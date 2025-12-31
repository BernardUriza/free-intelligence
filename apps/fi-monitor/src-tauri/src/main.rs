// FI Monitor - Tauri Application
// Lightweight desktop app for LLM observability

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

struct EdgeServer(Mutex<Option<std::process::Child>>);

fn start_edge_server() -> Option<std::process::Child> {
    // Find Python executable
    let python = if cfg!(windows) {
        "python"
    } else {
        "python3"
    };

    // Get the path to fi_edge module
    // In dev: relative to the project root
    // In production: bundled with the app
    let result = Command::new(python)
        .args(["-m", "fi_edge.server"])
        .env("PYTHONPATH", get_backend_path())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();

    match result {
        Ok(child) => {
            println!("[FI Monitor] Edge server started (PID: {})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("[FI Monitor] Failed to start edge server: {}", e);
            None
        }
    }
}

fn get_backend_path() -> String {
    // In development, use relative path from the app
    // In production, this would be bundled differently
    if cfg!(debug_assertions) {
        // Development: go up from apps/fi-monitor/src-tauri to backend/src
        let mut path = std::env::current_dir().unwrap_or_default();
        // Try to find backend/src relative to current dir or parent dirs
        for _ in 0..5 {
            let backend_path = path.join("backend").join("src");
            if backend_path.exists() {
                return backend_path.to_string_lossy().to_string();
            }
            if !path.pop() {
                break;
            }
        }
        // Fallback: assume we're in the project root
        "backend/src".to_string()
    } else {
        // Production: bundled path (adjust as needed for your packaging)
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("backend").join("src")))
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| "backend/src".to_string())
    }
}

fn main() {
    tauri::Builder::default()
        .manage(EdgeServer(Mutex::new(None)))
        .setup(|app| {
            // Start edge server on app launch
            let child = start_edge_server();
            let state = app.state::<EdgeServer>();
            *state.0.lock().unwrap() = child;
            Ok(())
        })
        .on_window_event(|event| {
            // Kill edge server when app closes
            if let tauri::WindowEvent::Destroyed = event.event() {
                if let Some(state) = event.window().try_state::<EdgeServer>() {
                    if let Some(mut child) = state.0.lock().unwrap().take() {
                        println!("[FI Monitor] Stopping edge server...");
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
