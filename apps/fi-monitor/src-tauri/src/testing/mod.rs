// Testing — service status, LLM and RAG smoke tests.

mod llm;
mod rag;
mod status;

// Shared types used by submodules
pub(crate) use llm::{test_llm_health, test_ollama};
pub(crate) use status::get_status;

use serde::{Deserialize, Serialize};

/// Result of a test query (LLM or RAG).
#[derive(Serialize, Clone)]
pub(crate) struct TestResult {
    pub(super) category: String,
    pub(super) question: String,
    pub(super) answer: String,
    pub(super) elapsed_ms: u64,
    pub(super) timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) rag_metadata: Option<serde_json::Value>,
}

/// Simple smoke test response — no complex metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct SmokeTestResult {
    pub(super) success: bool,
    pub(super) latency_ms: u64,
    pub(super) response: String,
    pub(super) error: Option<String>,
}

/// Shared Ollama generate request (DRY: used by both LLM test and health check).
#[derive(Serialize)]
pub(super) struct OllamaGenerateRequest {
    pub(super) model: String,
    pub(super) prompt: String,
    pub(super) stream: bool,
}

/// Shared Ollama generate response.
#[derive(Deserialize)]
pub(super) struct OllamaGenerateResponse {
    pub(super) response: String,
}
