use crate::state::*;
use crate::utils::{format_size, format_time_ago};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::time::Duration;
use tauri::Emitter;
use tokio::time::sleep;

pub(crate) async fn check_ollama() -> bool {
    let Ok(client) = http_client(3) else {
        return false;
    };
    client
        .get(format!("{}/api/tags", ollama_base_url()))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

pub(crate) async fn get_ollama_models() -> Vec<String> {
    #[derive(Deserialize)]
    struct ModelsResponse {
        models: Vec<Model>,
    }
    #[derive(Deserialize)]
    struct Model {
        name: String,
    }

    let Ok(client) = http_client(5) else {
        return vec![];
    };

    match client.get(format!("{}/api/tags", ollama_base_url())).send().await {
        Ok(response) => match response.json::<ModelsResponse>().await {
            Ok(r) => r.models.into_iter().map(|m| m.name).collect(),
            Err(_) => vec![],
        },
        Err(_) => vec![],
    }
}

// ============================================================================
// Model Management (Ollama API)
// ============================================================================

#[derive(Serialize, Clone)]
pub(crate) struct OllamaModelInfo {
    name: String,
    size: String,
    modified: String,
    digest: String,
}

// ============================================================================
// Environment Variables Management
// ============================================================================

#[derive(Serialize, Deserialize, Clone)]
pub(crate) struct EnvVar {
    key: String,
    value: String,
}

fn get_env_file_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("ollama.env")
}

// ============================================================================
// Tauri Commands
// ============================================================================

#[tauri::command]
pub(crate) async fn list_ollama_models_detailed() -> Result<Vec<OllamaModelInfo>, String> {
    #[derive(Deserialize)]
    struct ModelsResponse {
        models: Vec<ModelDetail>,
    }

    #[derive(Deserialize)]
    struct ModelDetail {
        name: String,
        size: u64,
        modified_at: String,
        digest: String,
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let response = client
        .get(format!("{}/api/tags", ollama_base_url()))
        .send()
        .await
        .map_err(|e| format!("Failed to fetch models: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Ollama API returned {}", response.status()));
    }

    let data: ModelsResponse = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let models: Vec<OllamaModelInfo> = data
        .models
        .into_iter()
        .map(|m| OllamaModelInfo {
            name: m.name,
            size: format_size(m.size),
            modified: format_time_ago(&m.modified_at),
            digest: m.digest[..12].to_string(), // Short digest
        })
        .collect();

    Ok(models)
}

#[tauri::command]
pub(crate) async fn pull_ollama_model(
    model_name: String,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    println!("[FI Monitor] Pulling model: {}", model_name);

    app_handle
        .emit("model-pull-started", model_name.clone())
        .map_err(|e| e.to_string())?;

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(600)) // 10 minutes
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    #[derive(Serialize)]
    struct PullRequest {
        name: String,
        stream: bool,
    }

    let response = client
        .post(format!("{}/api/pull", ollama_base_url()))
        .json(&PullRequest {
            name: model_name.clone(),
            stream: false,
        })
        .send()
        .await
        .map_err(|e| format!("Failed to pull model: {}", e))?;

    if response.status().is_success() {
        println!("[FI Monitor] Model pulled successfully: {}", model_name);
        app_handle
            .emit("model-pull-completed", model_name)
            .map_err(|e| e.to_string())?;
        Ok(())
    } else {
        let error_msg = format!("Pull failed with status: {}", response.status());
        println!("[FI Monitor] {}", error_msg);
        app_handle
            .emit("model-pull-failed", error_msg.clone())
            .map_err(|e| e.to_string())?;
        Err(error_msg)
    }
}

#[tauri::command]
pub(crate) async fn delete_ollama_model(model_name: String) -> Result<(), String> {
    println!("[FI Monitor] Deleting model: {}", model_name);

    let client = reqwest::Client::new();

    #[derive(Serialize)]
    struct DeleteRequest {
        name: String,
    }

    let response = client
        .delete(format!("{}/api/delete", ollama_base_url()))
        .json(&DeleteRequest {
            name: model_name.clone(),
        })
        .send()
        .await
        .map_err(|e| format!("Failed to delete model: {}", e))?;

    if response.status().is_success() {
        println!(
            "[FI Monitor] Model deleted successfully: {}",
            model_name
        );
        Ok(())
    } else {
        let error_msg = format!("Delete failed with status: {}", response.status());
        println!("[FI Monitor] {}", error_msg);
        Err(error_msg)
    }
}

#[tauri::command]
pub(crate) fn get_env_vars() -> Result<Vec<EnvVar>, String> {
    let env_path = get_env_file_path();

    if !env_path.exists() {
        // Return defaults if file doesn't exist
        return Ok(vec![
            EnvVar {
                key: "OLLAMA_NUM_PARALLEL".to_string(),
                value: "1".to_string(),
            },
            EnvVar {
                key: "OLLAMA_MAX_LOADED_MODELS".to_string(),
                value: "1".to_string(),
            },
            EnvVar {
                key: "OLLAMA_ORIGINS".to_string(),
                value: "*".to_string(),
            },
        ]);
    }

    let content = std::fs::read_to_string(&env_path)
        .map_err(|e| format!("Failed to read env file: {}", e))?;

    let vars: Vec<EnvVar> = content
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.starts_with('#'))
        .filter_map(|line| {
            let parts: Vec<&str> = line.splitn(2, '=').collect();
            if parts.len() == 2 {
                Some(EnvVar {
                    key: parts[0].trim().to_string(),
                    value: parts[1].trim().to_string(),
                })
            } else {
                None
            }
        })
        .collect();

    Ok(vars)
}

#[tauri::command]
pub(crate) fn set_env_vars(vars: Vec<EnvVar>) -> Result<(), String> {
    let env_path = get_env_file_path();

    if let Some(parent) = env_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config dir: {}", e))?;
    }

    let mut content = String::from("# Ollama Environment Variables\n");
    content.push_str("# Generated by FI Monitor\n\n");

    for var in vars {
        content.push_str(&format!("{}={}\n", var.key, var.value));
    }

    std::fs::write(&env_path, content)
        .map_err(|e| format!("Failed to write env file: {}", e))?;

    println!(
        "[FI Monitor] Environment variables saved to {:?}",
        env_path
    );
    Ok(())
}

#[tauri::command]
pub(crate) async fn start_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    if check_ollama().await {
        *state.ollama_running.lock().unwrap() = true;
        return Ok(true);
    }
    println!("[FI Monitor] Starting Ollama...");
    let result = Command::new("ollama")
        .arg("serve")
        .env("OLLAMA_ORIGINS", "*")
        .env("OLLAMA_HOST", format!("0.0.0.0:{}", OLLAMA_PORT))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
    match result {
        Ok(child) => {
            *state.ollama_process.lock().unwrap() = Some(child.id());
            for _ in 0..30 {
                sleep(Duration::from_millis(500)).await;
                if check_ollama().await {
                    *state.ollama_running.lock().unwrap() = true;
                    println!("[FI Monitor] Ollama started (PID: {})", child.id());
                    return Ok(true);
                }
            }
            Err("Ollama started but not responding".to_string())
        }
        Err(e) => Err(format!("Failed to start Ollama: {}", e)),
    }
}

#[tauri::command]
pub(crate) async fn stop_ollama(state: tauri::State<'_, Arc<AppState>>) -> Result<bool, String> {
    println!("[FI Monitor] Stopping Ollama...");

    if let Some(pid) = state.ollama_process.lock().unwrap().take() {
        // Kill our own process by PID (precise -- won't touch user's other ollama instances)
        println!("[FI Monitor] Killing Ollama PID {}", pid);
        kill_process(pid);
    } else {
        // Fallback: ollama was running before FI Monitor started, kill by name
        #[cfg(target_os = "windows")]
        kill_process_by_name("ollama.exe");
        #[cfg(not(target_os = "windows"))]
        kill_process_by_name("ollama");
    }

    *state.ollama_running.lock().unwrap() = false;
    Ok(true)
}
