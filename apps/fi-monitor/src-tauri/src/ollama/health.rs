// Health — Ollama health check and model listing helpers.
// These are reusable across modules (tunnel.rs, testing.rs, main.rs).

use serde::Deserialize;

use crate::state::{http_client, ollama_base_url};

/// Check if Ollama is responding to API requests.
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

/// Fetch the list of model names from Ollama.
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

    match client
        .get(format!("{}/api/tags", ollama_base_url()))
        .send()
        .await
    {
        Ok(response) => match response.json::<ModelsResponse>().await {
            Ok(r) => r.models.into_iter().map(|m| m.name).collect(),
            Err(_) => vec![],
        },
        Err(_) => vec![],
    }
}
