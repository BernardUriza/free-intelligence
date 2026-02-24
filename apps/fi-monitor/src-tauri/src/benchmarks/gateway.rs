// Gateway benchmark — health check latency and routing overhead.

use std::time::Instant;

use super::GatewayBenchmark;
use crate::state::{gateway_base_url, http_client, rag_service_base_url};

/// Benchmark the gateway: health check latency and proxy-vs-direct routing overhead.
#[tauri::command]
pub(crate) async fn benchmark_gateway() -> Result<GatewayBenchmark, String> {
    println!("[FI Monitor] Starting Gateway benchmark...");

    let client = http_client(30)?;

    // 1. Health check latency
    let start = Instant::now();
    let _ = client
        .get(format!("{}/gateway/health", gateway_base_url()))
        .send()
        .await
        .map_err(|e| format!("Gateway health check failed: {}", e))?;
    let health_check_ms = start.elapsed().as_millis() as u64;

    // 2. Routing overhead (gateway proxy vs direct)
    let start = Instant::now();
    let _ = client
        .get(format!("{}/rag/health", gateway_base_url()))
        .send()
        .await
        .map_err(|e| format!("Gateway proxy failed: {}", e))?;
    let gateway_proxy_ms = start.elapsed().as_millis() as u64;

    let start = Instant::now();
    let _ = client
        .get(format!("{}/rag/health", rag_service_base_url()))
        .send()
        .await
        .map_err(|e| format!("Direct RAG health check failed: {}", e))?;
    let direct_ms = start.elapsed().as_millis() as u64;

    let routing_overhead_ms = gateway_proxy_ms as i64 - direct_ms as i64;

    println!("[FI Monitor] Gateway benchmark complete");

    Ok(GatewayBenchmark {
        health_check_ms,
        routing_overhead_ms,
    })
}
