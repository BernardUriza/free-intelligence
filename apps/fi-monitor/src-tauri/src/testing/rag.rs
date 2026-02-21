// RAG query testing.

use std::time::Instant;

use serde::{Deserialize, Serialize};

use super::TestResult;
use crate::services::check_rag_service;
use crate::state::{http_client, rag_service_base_url};

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

/// Execute a RAG query and return a [`TestResult`] with chunk metadata.
pub(super) async fn test_rag_query(query_text: String) -> Result<TestResult, String> {
    if !check_rag_service().await {
        return Err("RAG Service not running. Start it from the UI button.".to_string());
    }

    println!("[FI Monitor] RAG Testing: {}", query_text);
    let start = Instant::now();

    let client = http_client(60)?;

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

    let full_answer = format_rag_answer(&rag_res);

    Ok(TestResult {
        category: "rag".to_string(),
        question: query_text,
        answer: full_answer,
        elapsed_ms,
        timestamp: chrono::Utc::now().to_rfc3339(),
        rag_metadata: Some(build_rag_metadata(&rag_res)),
    })
}

/// Format the RAG answer with appended chunk sources.
fn format_rag_answer(rag_res: &RagResponse) -> String {
    let mut answer = rag_res.answer.clone();
    answer.push_str(&format!(
        "\n\nSources ({} chunks):",
        rag_res.chunks.len()
    ));
    for (i, chunk) in rag_res.chunks.iter().take(3).enumerate() {
        answer.push_str(&format!(
            "\n{}. {} (relevance: {:.2})",
            i + 1,
            chunk.text.chars().take(100).collect::<String>(),
            chunk.relevance
        ));
    }
    answer
}

/// Build the JSON metadata blob for a RAG result.
fn build_rag_metadata(rag_res: &RagResponse) -> serde_json::Value {
    serde_json::json!({
        "total_chunks": rag_res.metadata.total_chunks,
        "embedding_latency_ms": rag_res.metadata.embedding_latency_ms,
        "chunks": rag_res.chunks.iter().map(|c| {
            serde_json::json!({
                "text": c.text,
                "relevance": c.relevance
            })
        }).collect::<Vec<_>>()
    })
}
