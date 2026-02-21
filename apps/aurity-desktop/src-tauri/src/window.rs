// Window — splash/main window transition, status events, deep link registration.

use log::info;
use tauri::{Emitter, Listener, Manager};
use tauri_plugin_deep_link::DeepLinkExt;

use crate::constants::{FALLBACK_WINDOW_TIMEOUT, LOCALHOST, MIN_SPLASH_DURATION};

/// Emit loading status to splashscreen
pub(crate) fn emit_status(app: &tauri::AppHandle, message: &str) {
    let _ = app.emit("loading-status", message);
}

/// Register deep link handlers for OAuth callbacks.
/// On macOS: uses the native on_open_url handler.
/// On Linux/Windows: checks CLI args for deep link URLs passed at first launch.
pub(crate) fn register_deep_links(app: &tauri::App) {
    let app_handle = app.handle().clone();

    #[cfg(target_os = "macos")]
    {
        let dl_handle = app_handle.clone();
        app.deep_link().on_open_url(move |event| {
            for url in event.urls() {
                let url_str = url.to_string();
                if url_str.starts_with("aurity://") {
                    info!("Deep link received: {}", url_str);
                    let _ = dl_handle.emit("deep-link-received", url_str);
                }
            }
        });
    }

    #[cfg(not(target_os = "macos"))]
    {
        for arg in std::env::args() {
            if arg.starts_with("aurity://") {
                info!("Deep link from args: {}", arg);
                let _ = app_handle.emit("deep-link-received", arg);
            }
        }
    }
}

/// Manage the splash → main window transition.
/// Waits for the "frontend-ready" event, enforcing a minimum 15s splash for branding,
/// with a 20s fallback timeout.
pub(crate) fn setup_window_transition(app_handle: &tauri::AppHandle, port: u16) {
    let Some(main_window) = app_handle.get_webview_window("main") else {
        return;
    };

    // Inject backend URL into main window
    let js = format!(
        "window.__AURITY_BACKEND_URL__ = 'http://{}:{}';",
        LOCALHOST, port
    );
    let _ = main_window.eval(&js);

    // Wait for frontend ready signal before showing main window
    // Minimum 15 seconds splash for branding animation
    let splash_start = std::time::Instant::now();
    let ready_handle = app_handle.clone();
    main_window.listen("frontend-ready", move |_| {
        let elapsed = splash_start.elapsed();

        if elapsed < MIN_SPLASH_DURATION {
            let remaining = MIN_SPLASH_DURATION - elapsed;
            info!(
                "Frontend ready - waiting {:.1}s more for splash animation",
                remaining.as_secs_f32()
            );
            let handle = ready_handle.clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(remaining).await;
                show_main_close_splash(&handle);
            });
        } else {
            info!("Frontend ready - showing main window and closing splash");
            show_main_close_splash(&ready_handle);
        }
    });

    // Fallback: show main and close splash after 20s if frontend doesn't respond
    let fallback_handle = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(FALLBACK_WINDOW_TIMEOUT).await;
        if let Some(main) = fallback_handle.get_webview_window("main") {
            if !main.is_visible().unwrap_or(true) {
                info!("Fallback: showing main window after timeout");
                let _ = main.show();
                let _ = main.set_focus();
            }
        }
        if let Some(splash) = fallback_handle.get_webview_window("splashscreen") {
            info!("Fallback: closing splash after timeout");
            let _ = splash.close();
            let _ = fallback_handle.emit("splash-closed", ());
        }
    });
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/// Show the main window and close the splash screen.
fn show_main_close_splash(handle: &tauri::AppHandle) {
    if let Some(main) = handle.get_webview_window("main") {
        let _ = main.show();
        let _ = main.set_focus();
    }
    if let Some(splash) = handle.get_webview_window("splashscreen") {
        let _ = splash.close();
        let _ = handle.emit("splash-closed", ());
    }
}
