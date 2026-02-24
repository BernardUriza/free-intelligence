// Benchmarks Module
//
// Performance benchmarking suite for RAG Service, Ollama, and Gateway.
// Results are persisted to ~/.config/fi-monitor/benchmarks.json.
//
// Module structure (SRP):
//   persistence.rs — Load/save benchmark history to disk
//   rag.rs         — RAG Service benchmark (embedding batches, throughput)
//   ollama.rs      — Ollama benchmark (generation latency, tokens/sec)
//   gateway.rs     — Gateway benchmark (health latency, routing overhead)
//   suite.rs       — Full benchmark suite orchestration + history query

mod gateway;
mod ollama;
mod persistence;
mod rag;
mod suite;

use serde::{Deserialize, Serialize};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct RagBenchmark {
    pub(crate) single_query_ms: u64,
    pub(crate) batch_10_ms: u64,
    pub(crate) batch_32_ms: u64,
    pub(crate) batch_100_ms: u64,
    pub(crate) throughput_qps: f64,
    pub(crate) gpu_memory_mb: f64,
    pub(crate) device: String,
    pub(crate) gpu_name: Option<String>,
    pub(crate) model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct OllamaBenchmark {
    pub(crate) single_query_ms: u64,
    pub(crate) batch_5_avg_ms: u64,
    pub(crate) tokens_per_sec: f64,
    pub(crate) model: String,
    pub(crate) eval_duration_ms: u64,
    pub(crate) eval_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct GatewayBenchmark {
    pub(crate) health_check_ms: u64,
    pub(crate) routing_overhead_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct BenchmarkSuite {
    pub(crate) timestamp: String,
    pub(crate) rag_service: Option<RagBenchmark>,
    pub(crate) ollama: Option<OllamaBenchmark>,
    pub(crate) gateway: Option<GatewayBenchmark>,
    pub(crate) total_duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct BenchmarkHistory {
    pub(crate) results: Vec<BenchmarkSuite>,
}

// =============================================================================
// RE-EXPORTS (Tauri commands)
// =============================================================================

pub(crate) use gateway::benchmark_gateway;
pub(crate) use ollama::benchmark_ollama;
pub(crate) use rag::benchmark_rag_service;
pub(crate) use suite::{benchmark_all, get_benchmark_history};
