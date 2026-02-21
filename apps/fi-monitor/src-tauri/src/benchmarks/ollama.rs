// Ollama benchmark — generation latency and tokens/sec.

use std::time::Instant;

use serde::{Deserialize, Serialize};

use super::OllamaBenchmark;
use crate::state::{http_client, ollama_base_url};

/// Default model used for benchmarks.
const BENCHMARK_MODEL: &str = "qwen3:1.7b";

#[derive(Serialize)]
struct GenerateRequest {
    model: String,
    prompt: String,
    stream: bool,
}

#[derive(Deserialize)]
struct GenerateResponse {
    #[allow(dead_code)]
    response: String,
    #[serde(default)]
    eval_duration: u64,
    #[serde(default)]
    eval_count: u64,
}

/// Benchmark Ollama: single query latency, batch-5 average, tokens/sec.
#[tauri::command]
pub(crate) async fn benchmark_ollama() -> Result<OllamaBenchmark, String> {
    println!("[FI Monitor] Starting Ollama benchmark...");

    let client = http_client(60)?;

    // 1. Single query
    let start = Instant::now();
    let resp = client
        .post(format!("{}/api/generate", ollama_base_url()))
        .json(&GenerateRequest {
            model: BENCHMARK_MODEL.to_string(),
            prompt: "What is 2+2? Answer only the number.".to_string(),
            stream: false,
        })
        .send()
        .await
        .map_err(|e| format!("Single query failed: {}", e))?
        .json::<GenerateResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    let single_query_ms = start.elapsed().as_millis() as u64;

    let eval_duration_ms = resp.eval_duration / 1_000_000; // ns → ms
    let eval_count = resp.eval_count;

    // 2. Batch 5 queries (sequential)
    let mut total_ms = 0u64;
    for i in 0..5 {
        let start = Instant::now();
        let _ = client
            .post(format!("{}/api/generate", ollama_base_url()))
            .json(&GenerateRequest {
                model: BENCHMARK_MODEL.to_string(),
                prompt: format!("What is {}+{}? Answer only the number.", i, i),
                stream: false,
            })
            .send()
            .await
            .map_err(|e| format!("Batch query {} failed: {}", i, e))?;
        total_ms += start.elapsed().as_millis() as u64;
    }
    let batch_5_avg_ms = total_ms / 5;

    // 3. Calculate tokens/sec
    let tokens_per_sec = if eval_duration_ms > 0 {
        (eval_count as f64 / (eval_duration_ms as f64 / 1000.0)).round()
    } else {
        0.0
    };

    println!("[FI Monitor] Ollama benchmark complete");

    Ok(OllamaBenchmark {
        single_query_ms,
        batch_5_avg_ms,
        tokens_per_sec,
        model: BENCHMARK_MODEL.to_string(),
        eval_duration_ms,
        eval_count,
    })
}
