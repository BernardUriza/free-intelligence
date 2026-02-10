use tauri_plugin_autostart::ManagerExt;

#[tauri::command]
pub(crate) async fn is_autostart_enabled(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())
}

#[tauri::command]
pub(crate) async fn enable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .enable()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}

#[tauri::command]
pub(crate) async fn disable_autostart(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .disable()
        .map_err(|e: tauri_plugin_autostart::Error| e.to_string())?;
    Ok(true)
}
