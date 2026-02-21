// Download — stream FI Monitor installer from GitHub Releases with progress events.

use log::info;
use tauri::Emitter;

use super::errors;
use super::paths;
use super::{DownloadProgress, MonitorError, DOWNLOAD_TIMEOUT};

/// Download FI Monitor installer from GitHub Releases.
/// Emits `fi-monitor-download-progress` events during the stream.
#[tauri::command]
pub async fn download_fi_monitor(app: tauri::AppHandle) -> Result<String, MonitorError> {
    let filename = paths::installer_filename();
    let download_url = paths::release_download_url();

    let installer_path = std::env::temp_dir().join(&filename);

    let client = reqwest::Client::builder()
        .timeout(DOWNLOAD_TIMEOUT)
        .build()
        .map_err(|e| {
            MonitorError::DownloadFailed(format!("Error al crear cliente HTTP: {}", e))
        })?;

    info!("Downloading FI Monitor from: {}", download_url);

    let response = client
        .get(&download_url)
        .send()
        .await
        .map_err(|e| errors::classify_network_error(&e))?;

    if !response.status().is_success() {
        return Err(errors::classify_http_status(response.status()));
    }

    stream_to_file(response, &installer_path, &app).await?;

    Ok(installer_path.to_string_lossy().to_string())
}

// ---------------------------------------------------------------------------
// Internal
// ---------------------------------------------------------------------------

/// Stream the response body to a file, emitting progress events.
async fn stream_to_file(
    response: reqwest::Response,
    path: &std::path::Path,
    app: &tauri::AppHandle,
) -> Result<(), MonitorError> {
    use futures_util::StreamExt;
    use tokio::io::AsyncWriteExt;

    let total_size = response.content_length().unwrap_or(0);
    let mut downloaded: u64 = 0;

    let mut file = tokio::fs::File::create(path)
        .await
        .map_err(|e| MonitorError::Io(format!("Failed to create installer file: {}", e)))?;

    let mut stream = response.bytes_stream();

    while let Some(chunk) = stream.next().await {
        let chunk =
            chunk.map_err(|e| MonitorError::DownloadFailed(format!("Download error: {}", e)))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| MonitorError::Io(format!("Write error: {}", e)))?;

        downloaded += chunk.len() as u64;

        let progress = DownloadProgress {
            downloaded_bytes: downloaded,
            total_bytes: total_size,
            percentage: if total_size > 0 {
                (downloaded as f32 / total_size as f32) * 100.0
            } else {
                0.0
            },
        };

        let _ = app.emit("fi-monitor-download-progress", progress);
    }

    file.flush()
        .await
        .map_err(|e| MonitorError::Io(format!("Flush error: {}", e)))?;

    Ok(())
}
