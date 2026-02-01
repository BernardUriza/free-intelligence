#!/usr/bin/env python3.14
"""
RAG Testing Tool - Gradio UI
Visualización interactiva para testing de RAG Service con embeddings GPU.
"""

import os
import json
from typing import List, Tuple
import gradio as gr
import requests
from PyPDF2 import PdfReader

# Configuration
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:11435")
RAG_API_KEY = os.getenv("RAG_API_KEY", "test-api-key-12345")

# Global state
document_chunks: List[str] = []
chunk_embeddings: List[List[float]] = []


# ========== PDF Processing ==========

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


# ========== RAG Service API Calls ==========

def health_check() -> Tuple[str, str]:
    """Check RAG Service health."""
    try:
        response = requests.get(
            f"{RAG_SERVICE_URL}/health",
            headers={"Authorization": f"Bearer {RAG_API_KEY}"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            status = "✅ Healthy"
            details = json.dumps(data, indent=2)
        else:
            status = f"❌ Error {response.status_code}"
            details = response.text

        return status, details

    except Exception as e:
        return f"❌ Connection Failed", str(e)


def generate_embeddings(chunks: List[str]) -> Tuple[str, str]:
    """Generate embeddings for text chunks using RAG Service."""
    global chunk_embeddings

    try:
        response = requests.post(
            f"{RAG_SERVICE_URL}/api/embeddings",
            headers={
                "Authorization": f"Bearer {RAG_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"texts": chunks},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            chunk_embeddings = data.get("embeddings", [])

            status = f"✅ Generated {len(chunk_embeddings)} embeddings"
            details = json.dumps({
                "num_embeddings": len(chunk_embeddings),
                "embedding_dim": len(chunk_embeddings[0]) if chunk_embeddings else 0,
                "model": data.get("model", "unknown"),
                "processing_time_ms": data.get("processing_time_ms", 0)
            }, indent=2)
        else:
            status = f"❌ Error {response.status_code}"
            details = response.text

        return status, details

    except Exception as e:
        return f"❌ Request Failed", str(e)


def semantic_search(query: str, top_k: int = 3) -> Tuple[str, str]:
    """Perform semantic search using RAG Service."""
    global document_chunks, chunk_embeddings

    if not document_chunks:
        return "⚠️ No documents loaded", "Upload and process a document first"

    try:
        response = requests.post(
            f"{RAG_SERVICE_URL}/api/search",
            headers={
                "Authorization": f"Bearer {RAG_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "document_chunks": document_chunks,
                "top_k": top_k
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            # Format results
            formatted = ""
            for i, result in enumerate(results, 1):
                formatted += f"\n{'='*60}\n"
                formatted += f"Result {i} (Score: {result['score']:.4f})\n"
                formatted += f"{'='*60}\n"
                formatted += result['text'] + "\n"

            status = f"✅ Found {len(results)} results"
            details = json.dumps({
                "query": query,
                "num_results": len(results),
                "processing_time_ms": data.get("processing_time_ms", 0)
            }, indent=2)

            return status + "\n\n" + formatted, details
        else:
            status = f"❌ Error {response.status_code}"
            details = response.text

        return status, details

    except Exception as e:
        return f"❌ Search Failed", str(e)


# ========== GPU Metrics ==========

def get_gpu_metrics() -> str:
    """Fetch GPU metrics from RAG Service."""
    try:
        response = requests.get(
            f"{RAG_SERVICE_URL}/api/metrics",
            headers={"Authorization": f"Bearer {RAG_API_KEY}"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            # Format GPU metrics
            metrics = "GPU METRICS\n" + "="*60 + "\n\n"

            if "gpu" in data:
                gpu = data["gpu"]
                metrics += f"Device: {gpu.get('device_name', 'N/A')}\n"
                metrics += f"Utilization: {gpu.get('utilization', 0)}%\n"
                metrics += f"Memory Used: {gpu.get('memory_used_mb', 0):.2f} MB\n"
                metrics += f"Memory Total: {gpu.get('memory_total_mb', 0):.2f} MB\n"
                metrics += f"Temperature: {gpu.get('temperature', 0)}°C\n"
            else:
                metrics += "GPU metrics not available\n"

            return metrics
        else:
            return f"Error fetching metrics: {response.status_code}\n{response.text}"

    except Exception as e:
        return f"Error: {str(e)}"


# ========== Gradio UI Handlers ==========

def process_pdf(pdf_file) -> Tuple[str, str, str]:
    """Process uploaded PDF and generate embeddings."""
    global document_chunks

    if pdf_file is None:
        return "⚠️ No file uploaded", "", ""

    # Extract text
    text = extract_text_from_pdf(pdf_file.name)

    if text.startswith("Error"):
        return text, "", ""

    # Chunk text
    document_chunks = chunk_text(text)

    # Generate embeddings
    status, details = generate_embeddings(document_chunks)

    summary = f"✅ Processed PDF successfully\n"
    summary += f"- Total text length: {len(text)} characters\n"
    summary += f"- Number of chunks: {len(document_chunks)}\n"
    summary += f"- Embeddings: {status}\n"

    return summary, text[:1000] + "..." if len(text) > 1000 else text, details


def ask_question(question: str, top_k: int) -> Tuple[str, str]:
    """Answer question using semantic search."""
    if not question.strip():
        return "⚠️ Please enter a question", ""

    return semantic_search(question, top_k)


# ========== Gradio Interface ==========

def create_ui():
    """Create Gradio interface."""

    with gr.Blocks(title="RAG Testing Tool", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔬 RAG Testing Tool")
        gr.Markdown("Interactive testing UI for RAG Service with GPU embeddings")

        with gr.Tabs():
            # Tab 1: PDF Upload & Processing
            with gr.Tab("📄 PDF Upload"):
                with gr.Row():
                    pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
                    process_btn = gr.Button("Process PDF", variant="primary")

                process_status = gr.Textbox(label="Processing Status", lines=5)

                with gr.Row():
                    with gr.Column():
                        extracted_text = gr.Textbox(label="Extracted Text (preview)", lines=10)
                    with gr.Column():
                        embedding_details = gr.Textbox(label="Embedding Details", lines=10)

                process_btn.click(
                    fn=process_pdf,
                    inputs=[pdf_input],
                    outputs=[process_status, extracted_text, embedding_details]
                )

            # Tab 2: Q&A Chat
            with gr.Tab("💬 Q&A Chat"):
                with gr.Row():
                    question_input = gr.Textbox(label="Your Question", placeholder="What is the diagnosis?")
                    top_k_slider = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Top K Results")

                search_btn = gr.Button("Search", variant="primary")

                search_results = gr.Textbox(label="Search Results", lines=15)
                search_details = gr.Textbox(label="Search Metadata", lines=5)

                search_btn.click(
                    fn=ask_question,
                    inputs=[question_input, top_k_slider],
                    outputs=[search_results, search_details]
                )

            # Tab 3: GPU Metrics
            with gr.Tab("📊 GPU Metrics"):
                gpu_output = gr.Textbox(label="GPU Status", lines=10)
                refresh_btn = gr.Button("Refresh Metrics", variant="primary")

                refresh_btn.click(
                    fn=get_gpu_metrics,
                    inputs=[],
                    outputs=[gpu_output]
                )

                # Auto-refresh on load
                demo.load(fn=get_gpu_metrics, inputs=[], outputs=[gpu_output])

            # Tab 4: Debug Panel
            with gr.Tab("🔧 Debug"):
                health_status = gr.Textbox(label="Health Status")
                health_details = gr.Textbox(label="Health Details", lines=10)
                health_btn = gr.Button("Check Health", variant="primary")

                health_btn.click(
                    fn=health_check,
                    inputs=[],
                    outputs=[health_status, health_details]
                )

                gr.Markdown("### Configuration")
                gr.Markdown(f"**RAG Service URL:** `{RAG_SERVICE_URL}`")
                gr.Markdown(f"**API Key:** `{RAG_API_KEY[:10]}...`")

    return demo


# ========== Main ==========

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
