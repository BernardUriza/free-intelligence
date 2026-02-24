// Service management — RAG Service and Gateway sidecar lifecycle.

mod gateway;
mod rag;
mod sidecar;

pub(crate) use gateway::*;
pub(crate) use rag::*;

use serde::Serialize;

/// RAG Service runtime statistics.
#[derive(Serialize, Clone, Default)]
pub(crate) struct RagStats {
    pub(super) gpu_memory_used_mb: u64,
    pub(super) gpu_memory_total_mb: u64,
    pub(super) gpu_device: String,
    pub(super) model_name: String,
    pub(super) embeddings_count: u64,
    pub(super) avg_query_ms: f64,
    pub(super) throughput_qps: f64,
}
