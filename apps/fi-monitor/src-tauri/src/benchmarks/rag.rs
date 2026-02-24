// RAG Service benchmark — embedding batch latency and throughput.

use std::time::Instant;

use serde::{Deserialize, Serialize};

use super::RagBenchmark;
use crate::state::{http_client, rag_service_base_url};

#[derive(Serialize)]
struct EmbedRequest {
    texts: Vec<String>,
}

#[derive(Deserialize)]
struct HealthResponse {
    device: String,
    gpu_name: Option<String>,
    gpu_memory_mb: Option<f64>,
    model: String,
}

/// Measure a single embed batch and return elapsed milliseconds.
async fn measure_embed_batch(
    client: &reqwest::Client,
    api_key: &str,
    batch_size: usize,
) -> Result<u64, String> {
    let texts: Vec<String> = (0..batch_size)
        .map(|i| format!("Test query {}", i))
        .collect();

    let start = Instant::now();
    let _ = client
        .post(format!("{}/rag/embed", rag_service_base_url()))
        .header("X-API-Key", api_key)
        .json(&EmbedRequest { texts })
        .send()
        .await
        .map_err(|e| format!("Batch {} failed: {}", batch_size, e))?;
    Ok(start.elapsed().as_millis() as u64)
}

/// Benchmark the RAG Service: single query, batch 10/32/100, throughput, GPU info.
#[tauri::command]
pub(crate) async fn benchmark_rag_service() -> Result<RagBenchmark, String> {
    println!("[FI Monitor] Starting RAG Service benchmark...");

    let api_key = std::env::var("RAG_API_KEY").unwrap_or_default();
    let client = http_client(30)?;

    // 1. Health check — get GPU info
    let health_resp = client
        .get(format!("{}/rag/health", rag_service_base_url()))
        .send()
        .await
        .map_err(|e| format!("Health check failed: {}", e))?
        .json::<HealthResponse>()
        .await
        .map_err(|e| format!("Failed to parse health response: {}", e))?;

    // 2. Single query
    let single_query_ms = measure_embed_batch(&client, &api_key, 1).await?;

    // 3-5. Batch queries
    let batch_10_ms = measure_embed_batch(&client, &api_key, 10).await?;
    let batch_32_ms = measure_embed_batch(&client, &api_key, 32).await?;
    let batch_100_ms = measure_embed_batch(&client, &api_key, 100).await?;

    let throughput_qps = (100.0 / (batch_100_ms as f64 / 1000.0)).round();

    println!("[FI Monitor] RAG Service benchmark complete");

    Ok(RagBenchmark {
        single_query_ms,
        batch_10_ms,
        batch_32_ms,
        batch_100_ms,
        throughput_qps,
        gpu_memory_mb: health_resp.gpu_memory_mb.unwrap_or(0.0),
        device: health_resp.device,
        gpu_name: health_resp.gpu_name,
        model: health_resp.model,
    })
}
