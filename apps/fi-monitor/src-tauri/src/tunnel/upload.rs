// Azure Blob upload, local backup persistence, and periodic re-upload.

use std::path::PathBuf;
use std::time::Duration;

use crate::state::AppConfig;

/// Upload tunnel URL to Azure Blob Storage with retry logic.
pub(super) fn upload_tunnel_url_to_azure(url: &str, config: &AppConfig) -> Result<(), String> {
    let azure_sas_url = config
        .azure_sas_url
        .clone()
        .or_else(|| std::env::var("FI_AZURE_TUNNEL_BLOB_SAS").ok())
        .unwrap_or_default();

    if azure_sas_url.is_empty() {
        println!("[FI Monitor] No Azure SAS URL configured, skipping upload");
        save_tunnel_url_locally(url)?;
        return Ok(());
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp,
        "version": "1.1",
        "services": {
            "ollama": format!("{}/api", url),
            "rag": format!("{}/rag", url),
            "gateway": format!("{}/gateway/health", url)
        }
    })
    .to_string();

    let max_retries = 3;
    let mut last_error = String::new();

    for attempt in 0..max_retries {
        if attempt > 0 {
            let delay = Duration::from_millis(500 * 2u64.pow(attempt as u32));
            println!("[FI Monitor] Retry {} in {:?}...", attempt + 1, delay);
            std::thread::sleep(delay);
        }

        println!(
            "[FI Monitor] Uploading tunnel URL to Azure (attempt {})...",
            attempt + 1
        );

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| format!("Client error: {}", e))?;

        match client
            .put(&azure_sas_url)
            .header("x-ms-blob-type", "BlockBlob")
            .header("Content-Type", "application/json")
            .body(content.clone())
            .send()
        {
            Ok(response) if response.status().is_success() => {
                println!("[FI Monitor] Tunnel URL uploaded to Azure");
                let _ = save_tunnel_url_locally(url);
                return Ok(());
            }
            Ok(response) => {
                last_error = format!(
                    "HTTP {}: {}",
                    response.status(),
                    response.status().canonical_reason().unwrap_or("Unknown")
                );
                println!("[FI Monitor] Azure returned: {}", last_error);
            }
            Err(e) => {
                last_error = format!("Request failed: {}", e);
                println!("[FI Monitor] {}", last_error);
            }
        }
    }

    println!(
        "[FI Monitor] Azure upload failed after {} retries, saving locally",
        max_retries
    );
    save_tunnel_url_locally(url)?;
    Err(last_error)
}

/// Save tunnel URL locally as backup.
pub(super) fn save_tunnel_url_locally(url: &str) -> Result<(), String> {
    let path = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("tunnel-url.json");

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let hostname = gethostname::gethostname().to_string_lossy().to_string();
    let timestamp = chrono::Utc::now().to_rfc3339();
    let content = serde_json::json!({
        "tunnel_url": url,
        "hostname": hostname,
        "updated_at": timestamp
    });

    let json = serde_json::to_string_pretty(&content).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Tunnel URL saved locally: {:?}", path);
    Ok(())
}

/// Read the tunnel URL file content.
pub(super) fn read_tunnel_file_content() -> Result<String, String> {
    let path = dirs::config_dir()
        .ok_or("Could not determine config directory")?
        .join("fi-monitor")
        .join("tunnel-url.json");

    if !path.exists() {
        return Err("Tunnel file not found. Start the tunnel to create it.".to_string());
    }

    std::fs::read_to_string(&path).map_err(|e| format!("Failed to read file: {}", e))
}

/// Periodically re-upload tunnel URL to keep timestamp fresh (every 5 minutes).
pub(super) fn start_periodic_upload(url: String, config: AppConfig) {
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(300));

            println!("[FI Monitor] Periodic re-upload of tunnel URL...");
            if let Err(e) = upload_tunnel_url_to_azure(&url, &config) {
                println!("[FI Monitor] Periodic upload failed: {}", e);
            }
        }
    });
}
