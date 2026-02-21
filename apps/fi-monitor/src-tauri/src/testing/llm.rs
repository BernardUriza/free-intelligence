// LLM testing — direct Ollama queries and health check.

use std::time::Instant;

use super::rag::test_rag_query;
use super::{OllamaGenerateRequest, OllamaGenerateResponse, SmokeTestResult, TestResult};
use crate::ollama::check_ollama;
use crate::state::{http_client, ollama_base_url};

/// Pre-defined question bank for random LLM tests.
const LLM_QUESTIONS: &[(&str, &str)] = &[
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

/// Test Ollama in either RAG or LLM mode.
///
/// Dispatches to [`test_rag_query`] or [`test_llm_query`] based on `mode`.
#[tauri::command]
pub(crate) async fn test_ollama(
    mode: Option<String>,
    question: Option<String>,
) -> Result<TestResult, String> {
    let test_mode = mode.unwrap_or_else(|| "llm".to_string());

    if test_mode == "rag" {
        let query_text = question.ok_or_else(|| "RAG mode requires a question".to_string())?;
        return test_rag_query(query_text).await;
    }

    test_llm_query(question).await
}

/// Execute an LLM query against Ollama and return a [`TestResult`].
async fn test_llm_query(question: Option<String>) -> Result<TestResult, String> {
    if !check_ollama().await {
        return Err("Ollama no esta ejecutandose".to_string());
    }

    let prompt = match question {
        Some(q) => q,
        None => pick_random_question(),
    };

    let category = if prompt.contains("raiz cuadrada") {
        "math"
    } else {
        "anatomy"
    };

    println!("[FI Monitor] LLM Testing: {}", prompt);
    let start = Instant::now();
    let client = http_client(60)?;

    let request = OllamaGenerateRequest {
        model: "qwen3:1.7b".to_string(),
        prompt: prompt.clone(),
        stream: false,
    };

    let response = client
        .post(format!("{}/api/generate", ollama_base_url()))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Error: {}", e))?;

    let res: OllamaGenerateResponse = response
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

/// Pick a pseudo-random question from the bank based on current timestamp.
fn pick_random_question() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let idx = (now % LLM_QUESTIONS.len() as u64) as usize;
    LLM_QUESTIONS[idx].1.to_string()
}

/// Smoke test for LLM health (simple 2+2 question).
#[tauri::command]
pub(crate) async fn test_llm_health() -> Result<SmokeTestResult, String> {
    if !check_ollama().await {
        return Ok(SmokeTestResult {
            success: false,
            latency_ms: 0,
            response: String::new(),
            error: Some("Ollama is not running".to_string()),
        });
    }

    let start = Instant::now();
    let client = http_client(15)?;

    let request = OllamaGenerateRequest {
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
            parse_health_response(response, latency_ms, &start).await
        }
        Err(e) => Ok(SmokeTestResult {
            success: false,
            latency_ms: start.elapsed().as_millis() as u64,
            response: String::new(),
            error: Some(format!("HTTP request failed: {}", e)),
        }),
    }
}

/// Parse the Ollama response for the health check and validate it contains "4".
async fn parse_health_response(
    response: reqwest::Response,
    latency_ms: u64,
    start: &Instant,
) -> Result<SmokeTestResult, String> {
    match response.json::<OllamaGenerateResponse>().await {
        Ok(ollama_res) => {
            let answer = ollama_res.response.trim().to_string();
            let success = answer.contains("4");

            Ok(SmokeTestResult {
                success,
                latency_ms,
                response: answer.clone(),
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
