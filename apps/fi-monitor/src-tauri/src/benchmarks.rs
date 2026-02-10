use crate::state::{gateway_base_url, http_client, ollama_base_url, rag_service_base_url};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tauri::Emitter;

// ============================================================================
// Benchmark Structures
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct RagBenchmark {
    single_query_ms: u64,
    batch_10_ms: u64,
    batch_32_ms: u64,
    batch_100_ms: u64,
    throughput_qps: f64,
    gpu_memory_mb: f64,
    device: String,
    gpu_name: Option<String>,
    model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct OllamaBenchmark {
    single_query_ms: u64,
    batch_5_avg_ms: u64,
    tokens_per_sec: f64,
    model: String,
    eval_duration_ms: u64,
    eval_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct GatewayBenchmark {
    health_check_ms: u64,
    routing_overhead_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct BenchmarkSuite {
    timestamp: String,
    rag_service: Option<RagBenchmark>,
    ollama: Option<OllamaBenchmark>,
    gateway: Option<GatewayBenchmark>,
    total_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct BenchmarkHistory {
    results: Vec<BenchmarkSuite>,
}

// ============================================================================
// Persistence
// ============================================================================

fn get_benchmarks_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("benchmarks.json")
}

fn load_benchmark_history() -> BenchmarkHistory {
    let path = get_benchmarks_path();
    if !path.exists() {
        return BenchmarkHistory { results: vec![] };
    }
    let content = std::fs::read_to_string(&path).unwrap_or_else(|_| "{}".to_string());
    serde_json::from_str(&content).unwrap_or(BenchmarkHistory { results: vec![] })
}

fn save_benchmark_result(result: BenchmarkSuite) -> Result<(), String> {
    let mut history = load_benchmark_history();
    history.results.insert(0, result); // Insert at front
    history.results.truncate(50); // Keep last 50

    let path = get_benchmarks_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&history).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Benchmark saved to {:?}", path);
    Ok(())
}

// ============================================================================
// Tauri Commands
// ============================================================================

#[tauri::command]
pub(crate) async fn benchmark_rag_service() -> Result<RagBenchmark, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting RAG Service benchmark...");

    let api_key = std::env::var("RAG_API_KEY").unwrap_or_default();
    let client = http_client(30)?;

    // 1. Health check - get GPU info
    #[derive(Deserialize)]
    struct HealthResponse {
        device: String,
        gpu_name: Option<String>,
        gpu_memory_mb: Option<f64>,
        model: String,
    }

    let health_resp = client
        .get(format!("{}/rag/health", rag_service_base_url()))
        .send()
        .await
        .map_err(|e| format!("Health check failed: {}", e))?
        .json::<HealthResponse>()
        .await
        .map_err(|e| format!("Failed to parse health response: {}", e))?;

    #[derive(Serialize)]
    struct EmbedRequest {
        texts: Vec<String>,
    }

    // 2. Single query
    let start = Instant::now();
    let _ = client
        .post(format!("{}/rag/embed", rag_service_base_url()))
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: vec!["Test embedding query".to_string()],
        })
        .send()
        .await
        .map_err(|e| format!("Single query failed: {}", e))?;
    let single_query_ms = start.elapsed().as_millis() as u64;

    // 3. Batch 10
    let start = Instant::now();
    let _ = client
        .post(format!("{}/rag/embed", rag_service_base_url()))
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..10).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 10 failed: {}", e))?;
    let batch_10_ms = start.elapsed().as_millis() as u64;

    // 4. Batch 32
    let start = Instant::now();
    let _ = client
        .post(format!("{}/rag/embed", rag_service_base_url()))
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..32).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 32 failed: {}", e))?;
    let batch_32_ms = start.elapsed().as_millis() as u64;

    // 5. Batch 100 + throughput
    let start = Instant::now();
    let _ = client
        .post(format!("{}/rag/embed", rag_service_base_url()))
        .header("X-API-Key", &api_key)
        .json(&EmbedRequest {
            texts: (0..100).map(|i| format!("Test query {}", i)).collect(),
        })
        .send()
        .await
        .map_err(|e| format!("Batch 100 failed: {}", e))?;
    let batch_100_ms = start.elapsed().as_millis() as u64;
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

#[tauri::command]
pub(crate) async fn benchmark_ollama() -> Result<OllamaBenchmark, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting Ollama benchmark...");

    let client = http_client(60)?;

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

    // 1. Single query
    let start = Instant::now();
    let resp = client
        .post(format!("{}/api/generate", ollama_base_url()))
        .json(&GenerateRequest {
            model: "qwen3:1.7b".to_string(),
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

    let eval_duration_ms = resp.eval_duration / 1_000_000; // ns to ms
    let eval_count = resp.eval_count;

    // 2. Batch 5 queries (sequential)
    let mut total_ms = 0u64;
    for i in 0..5 {
        let start = Instant::now();
        let _ = client
            .post(format!("{}/api/generate", ollama_base_url()))
            .json(&GenerateRequest {
                model: "qwen3:1.7b".to_string(),
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
        model: "qwen3:1.7b".to_string(),
        eval_duration_ms,
        eval_count,
    })
}

#[tauri::command]
pub(crate) async fn benchmark_gateway() -> Result<GatewayBenchmark, String> {
    use std::time::Instant;

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

#[tauri::command]
pub(crate) async fn benchmark_all(app: tauri::AppHandle) -> Result<BenchmarkSuite, String> {
    use std::time::Instant;

    println!("[FI Monitor] Starting benchmark suite...");
    let suite_start = Instant::now();

    // 1. RAG Service
    let rag_service = match benchmark_rag_service().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] RAG Service skipped: {}", e);
            None
        }
    };

    // 2. Ollama
    let ollama = match benchmark_ollama().await {
        Ok(result) => Some(result),
        Err(e) => {
            println!("[FI Monitor] Ollama skipped: {}", e);
            None
        }
    };

    // 3. Gateway
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

    // Save result
    save_benchmark_result(suite.clone())?;

    // Emit event
    let _ = app.emit("benchmark-complete", &suite);

    println!(
        "[FI Monitor] Benchmark suite complete in {}ms",
        total_duration_ms
    );

    Ok(suite)
}

#[tauri::command]
pub(crate) async fn get_benchmark_history() -> Result<BenchmarkHistory, String> {
    Ok(load_benchmark_history())
}
