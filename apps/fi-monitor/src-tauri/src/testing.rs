use crate::ollama::{check_ollama, get_ollama_models};
use crate::services::{check_gateway, check_rag_service};
use crate::state::*;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Serialize, Clone)]
pub(crate) struct TestResult {
    category: String,
    question: String,
    answer: String,
    elapsed_ms: u64,
    timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    rag_metadata: Option<serde_json::Value>,
}

/// Simple smoke test response - no complex metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct SmokeTestResult {
    success: bool,
    latency_ms: u64,
    response: String,
    error: Option<String>,
}

#[tauri::command]
pub(crate) async fn get_status(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<ServiceStatus, String> {
    let ollama_running = check_ollama().await;
    let models = if ollama_running {
        get_ollama_models().await
    } else {
        vec![]
    };
    let rag_service_running = check_rag_service().await;
    let gateway_running = check_gateway().await;

    *state.ollama_running.lock().unwrap() = ollama_running;
    *state.rag_service_running.lock().unwrap() = rag_service_running;
    *state.gateway_running.lock().unwrap() = gateway_running;

    Ok(ServiceStatus {
        ollama_running,
        ollama_models: models,
        tunnel_running: *state.tunnel_running.lock().unwrap(),
        tunnel_url: state.tunnel_url.lock().unwrap().clone(),
        rag_service_running,
        gateway_running,
        system_info: SystemInfo {
            platform: std::env::consts::OS.to_string(),
            hostname: gethostname::gethostname().to_string_lossy().to_string(),
        },
    })
}

#[tauri::command]
pub(crate) async fn test_ollama(
    mode: Option<String>,
    question: Option<String>,
) -> Result<TestResult, String> {
    use std::time::Instant;
    let test_mode = mode.unwrap_or_else(|| "llm".to_string());

    // RAG Mode: Query RAG Service
    if test_mode == "rag" {
        let query_text = question.ok_or_else(|| "RAG mode requires a question".to_string())?;

        // Check if RAG Service is running
        if !check_rag_service().await {
            return Err("RAG Service not running. Start it from the UI button.".to_string());
        }

        println!("[FI Monitor] RAG Testing: {}", query_text);
        let start = Instant::now();

        let client = http_client(60)?;

        #[derive(Serialize)]
        struct RagQuery {
            question: String,
            top_k: usize,
        }

        #[derive(Deserialize)]
        struct RagResponse {
            answer: String,
            chunks: Vec<RagChunk>,
            metadata: RagMetadata,
        }

        #[derive(Deserialize)]
        struct RagChunk {
            text: String,
            relevance: f32,
        }

        #[derive(Deserialize)]
        struct RagMetadata {
            total_chunks: usize,
            embedding_latency_ms: u64,
        }

        let request = RagQuery {
            question: query_text.clone(),
            top_k: 3,
        };

        let response = client
            .post(format!("{}/rag/query", rag_service_base_url()))
            .json(&request)
            .send()
            .await
            .map_err(|e| format!("RAG Service error: {}", e))?;

        let rag_res: RagResponse = response
            .json()
            .await
            .map_err(|e| format!("RAG parse error: {}", e))?;

        let elapsed_ms = start.elapsed().as_millis() as u64;
        println!("[FI Monitor] RAG Response in {}ms", elapsed_ms);

        // Format answer with chunks info
        let mut full_answer = rag_res.answer.clone();
        full_answer.push_str(&format!(
            "\n\nSources ({} chunks):",
            rag_res.chunks.len()
        ));
        for (i, chunk) in rag_res.chunks.iter().take(3).enumerate() {
            full_answer.push_str(&format!(
                "\n{}. {} (relevance: {:.2})",
                i + 1,
                chunk.text.chars().take(100).collect::<String>(),
                chunk.relevance
            ));
        }

        return Ok(TestResult {
            category: "rag".to_string(),
            question: query_text,
            answer: full_answer,
            elapsed_ms,
            timestamp: chrono::Utc::now().to_rfc3339(),
            rag_metadata: Some(serde_json::json!({
                "total_chunks": rag_res.metadata.total_chunks,
                "embedding_latency_ms": rag_res.metadata.embedding_latency_ms,
                "chunks": rag_res.chunks.iter().map(|c| {
                    serde_json::json!({
                        "text": c.text,
                        "relevance": c.relevance
                    })
                }).collect::<Vec<_>>()
            })),
        });
    }

    // LLM Mode: Original Ollama logic
    if !check_ollama().await {
        return Err("Ollama no esta ejecutandose".to_string());
    }

    let questions = [
        (
            "math",
            "Cual es la raiz cuadrada de 144? Responde solo el numero.",
        ),
        (
            "anatomy",
            "Explica brevemente que es el higado y su funcion principal.",
        ),
        (
            "math",
            "Cual es la raiz cuadrada de 256? Responde solo el numero.",
        ),
        (
            "anatomy",
            "Explica brevemente que es el corazon y su funcion principal.",
        ),
        (
            "math",
            "Cual es la raiz cuadrada de 625? Responde solo el numero.",
        ),
        (
            "anatomy",
            "Explica brevemente que son los pulmones y su funcion.",
        ),
    ];

    let prompt = if let Some(q) = question {
        q
    } else {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let idx = (now % questions.len() as u64) as usize;
        questions[idx].1.to_string()
    };

    let category = if prompt.contains("raiz cuadrada") {
        "math"
    } else {
        "anatomy"
    };

    println!("[FI Monitor] LLM Testing: {}", prompt);
    let start = Instant::now();
    let client = http_client(60)?;
    #[derive(Serialize)]
    struct Req {
        model: String,
        prompt: String,
        stream: bool,
    }
    #[derive(Deserialize)]
    struct Res {
        response: String,
    }
    let request = Req {
        model: "qwen3:1.7b".to_string(),
        prompt: prompt.to_string(),
        stream: false,
    };
    let response = client
        .post(format!("{}/api/generate", ollama_base_url()))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Error: {}", e))?;
    let res: Res = response
        .json()
        .await
        .map_err(|e| format!("Parse error: {}", e))?;
    let elapsed_ms = start.elapsed().as_millis() as u64;
    println!("[FI Monitor] LLM Response in {}ms", elapsed_ms);
    Ok(TestResult {
        category: category.to_string(),
        question: prompt,
        answer: res.response.trim().to_string(),
        elapsed_ms,
        timestamp: chrono::Utc::now().to_rfc3339(),
        rag_metadata: None,
    })
}

/// Smoke test for LLM health (simple 2+2 question)
#[tauri::command]
pub(crate) async fn test_llm_health() -> Result<SmokeTestResult, String> {
    use std::time::Instant;

    // 1. Check if Ollama is running (fail fast)
    if !check_ollama().await {
        return Ok(SmokeTestResult {
            success: false,
            latency_ms: 0,
            response: String::new(),
            error: Some("Ollama is not running".to_string()),
        });
    }

    // 2. Send simple test query
    let start = Instant::now();
    let client = http_client(15)?;

    #[derive(Serialize)]
    struct OllamaRequest {
        model: String,
        prompt: String,
        stream: bool,
    }

    #[derive(Deserialize)]
    struct OllamaResponse {
        response: String,
    }

    let request = OllamaRequest {
        model: "qwen2.5-coder:3b".to_string(),
        prompt: "What is 2+2? Answer with just the number, nothing else.".to_string(),
        stream: false,
    };

    match client
        .post(format!("{}/api/generate", ollama_base_url()))
        .json(&request)
        .send()
        .await
    {
        Ok(response) => {
            let latency_ms = start.elapsed().as_millis() as u64;

            match response.json::<OllamaResponse>().await {
                Ok(ollama_res) => {
                    let answer = ollama_res.response.trim();

                    // 3. Validate response contains "4"
                    let success = answer.contains("4");

                    Ok(SmokeTestResult {
                        success,
                        latency_ms,
                        response: answer.to_string(),
                        error: if success {
                            None
                        } else {
                            Some(format!("Expected '4' in response, got: {}", answer))
                        },
                    })
                }
                Err(e) => Ok(SmokeTestResult {
                    success: false,
                    latency_ms: start.elapsed().as_millis() as u64,
                    response: String::new(),
                    error: Some(format!("Failed to parse Ollama response: {}", e)),
                }),
            }
        }
        Err(e) => Ok(SmokeTestResult {
            success: false,
            latency_ms: start.elapsed().as_millis() as u64,
            response: String::new(),
            error: Some(format!("HTTP request failed: {}", e)),
        }),
    }
}
