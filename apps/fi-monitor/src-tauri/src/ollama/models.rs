// Models — detailed model listing, pull, and delete (Tauri commands).

use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::Emitter;

use crate::state::ollama_base_url;
use crate::utils::{format_size, format_time_ago};

/// Detailed model info returned to the frontend.
#[derive(Serialize, Clone)]
pub(crate) struct OllamaModelInfo {
    name: String,
    size: String,
    modified: String,
    digest: String,
}

/// List all Ollama models with size, modified date, and digest.
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

/// Pull (download) a model from the Ollama registry.
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

/// Delete a model from Ollama.
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
        println!("[FI Monitor] Model deleted successfully: {}", model_name);
        Ok(())
    } else {
        let error_msg = format!("Delete failed with status: {}", response.status());
        println!("[FI Monitor] {}", error_msg);
        Err(error_msg)
    }
}
