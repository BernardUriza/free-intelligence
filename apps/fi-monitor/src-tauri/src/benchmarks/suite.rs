// Benchmark suite orchestration and history retrieval.

use std::time::Instant;

use tauri::Emitter;

use super::gateway::benchmark_gateway;
use super::ollama::benchmark_ollama;
use super::persistence::{load_benchmark_history, save_benchmark_result};
use super::rag::benchmark_rag_service;
use super::{BenchmarkHistory, BenchmarkSuite};

/// Run all benchmarks (RAG, Ollama, Gateway), save and emit the result.
///
/// Each individual benchmark is run independently; failures are logged and
/// the corresponding field is set to `None` so the suite always completes.
#[tauri::command]
pub(crate) async fn benchmark_all(app: tauri::AppHandle) -> Result<BenchmarkSuite, String> {
    println!("[FI Monitor] Starting benchmark suite...");
    let suite_start = Instant::now();

    let rag_service = match benchmark_rag_service().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] RAG Service skipped: {}", e);
            None
        }
    };

    let ollama = match benchmark_ollama().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] Ollama skipped: {}", e);
            None
        }
    };

    let gateway = match benchmark_gateway().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] Gateway skipped: {}", e);
            None
        }
    };

    let total_duration_ms = suite_start.elapsed().as_millis() as u64;
    let timestamp = chrono::Local::now().to_rfc3339();

    let suite = BenchmarkSuite {
        timestamp,
        rag_service,
        ollama,
        gateway,
        total_duration_ms,
    };

    save_benchmark_result(suite.clone())?;
    let _ = app.emit("benchmark-complete", &suite);

    println!(
        "[FI Monitor] Benchmark suite complete in {}ms",
        total_duration_ms
    );

    Ok(suite)
}

/// Return the persisted benchmark history.
#[tauri::command]
pub(crate) async fn get_benchmark_history() -> Result<BenchmarkHistory, String> {
    Ok(load_benchmark_history())
}
