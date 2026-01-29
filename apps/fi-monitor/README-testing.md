# RAG Testing Tool - User Guide

Interactive Gradio UI for testing RAG Service with GPU embeddings.

---

## Quick Start

### 1. Install Dependencies

```bash
cd apps/fi-monitor
pip install -r requirements-dev.txt
```

### 2. Start RAG Service

In a separate terminal:

```bash
cd apps/fi-monitor/rag_service
python -m uvicorn main:app --host 0.0.0.0 --port 11435
```

Verify RAG Service is running:
```bash
curl http://localhost:11435/health
# Expected: {"status": "healthy", "gpu_available": true, ...}
```

### 3. Launch Testing UI

```bash
cd apps/fi-monitor
python test_rag_ui.py
```

Open browser at: **http://localhost:7860**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_SERVICE_URL` | `http://localhost:11435` | RAG Service endpoint |
| `RAG_API_KEY` | `test-api-key-12345` | Authentication key |

**Custom configuration:**
```bash
export RAG_SERVICE_URL=http://192.168.1.100:11435
export RAG_API_KEY=my-secret-key
python test_rag_ui.py
```

---

## Features

### 📄 Tab 1: PDF Upload & Processing

**Purpose:** Upload medical notes and generate embeddings

**Steps:**
1. Click "Upload PDF" and select a PDF file
   - Sample: `test_data/sample_medical_note.txt` (convert to PDF first)
2. Click "Process PDF"
3. Review:
   - **Processing Status:** Chunk count, embedding generation status
   - **Extracted Text:** Preview of first 1000 characters
   - **Embedding Details:** Model info, dimensions, processing time

**Expected Output:**
```
✅ Processed PDF successfully
- Total text length: 742 characters
- Number of chunks: 3
- Embeddings: ✅ Generated 3 embeddings
```

---

### 💬 Tab 2: Q&A Chat

**Purpose:** Semantic search over processed documents

**Steps:**
1. Ensure PDF is processed (Tab 1 completed)
2. Enter a question:
   - Example: "What is the diagnosis?"
   - Example: "What treatment was prescribed?"
3. Adjust "Top K Results" slider (default: 3)
4. Click "Search"

**Expected Output:**
```
✅ Found 3 results

============================================================
Result 1 (Score: 0.8521)
============================================================
DIAGNÓSTICO:
Migraña sin aura

TRATAMIENTO:
- Ibuprofeno 400mg cada 8 horas por 3 días
...
```

**Search Metadata:**
```json
{
  "query": "What is the diagnosis?",
  "num_results": 3,
  "processing_time_ms": 45
}
```

---

### 📊 Tab 3: GPU Metrics

**Purpose:** Monitor GPU usage during embedding generation

**Features:**
- Auto-refreshes on page load
- Manual refresh button
- Shows:
  - Device name (e.g., NVIDIA RTX 4090)
  - GPU utilization (%)
  - Memory usage (MB)
  - Temperature (°C)

**Expected Output:**
```
GPU METRICS
============================================================

Device: NVIDIA GeForce RTX 4090
Utilization: 23%
Memory Used: 1024.50 MB
Memory Total: 24564.00 MB
Temperature: 45°C
```

---

### 🔧 Tab 4: Debug Panel

**Purpose:** Verify RAG Service connectivity and configuration

**Features:**
- Health check endpoint
- Service configuration display
- API key validation

**Expected Output:**
```
Health Status: ✅ Healthy

Health Details:
{
  "status": "healthy",
  "gpu_available": true,
  "gpu_device": "NVIDIA GeForce RTX 4090",
  "model_loaded": true,
  "uptime_seconds": 120
}
```

---

## Troubleshooting

### Issue: "❌ Connection Failed"

**Cause:** RAG Service not running

**Fix:**
```bash
# Check if service is running
lsof -i :11435

# If not running, start it:
cd apps/fi-monitor/rag_service
python -m uvicorn main:app --host 0.0.0.0 --port 11435
```

---

### Issue: "⚠️ No documents loaded"

**Cause:** No PDF processed before asking questions

**Fix:**
1. Go to Tab 1 (PDF Upload)
2. Upload and process a PDF
3. Return to Tab 2 (Q&A Chat)

---

### Issue: "GPU metrics not available"

**Cause:** RAG Service running without GPU support

**Fix:**
```bash
# Verify GPU is accessible
nvidia-smi

# Check RAG Service logs for GPU initialization
# Expected: "GPU available: True"
```

---

### Issue: PDF upload fails with "Error reading PDF"

**Cause:** Corrupted PDF or unsupported format

**Fix:**
```bash
# Convert sample text to PDF using reportlab:
python -c "
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas('test_data/sample_medical_note.pdf', pagesize=letter)
with open('test_data/sample_medical_note.txt') as f:
    text = f.read()

y = 750
for line in text.split('\n'):
    c.drawString(50, y, line)
    y -= 15
    if y < 50:
        c.showPage()
        y = 750

c.save()
"

# Or use an existing PDF from real medical notes
```

---

## Verification Checklist

After installation, verify each feature works:

- [ ] **Service Health:** Tab 4 shows "✅ Healthy"
- [ ] **GPU Detected:** Tab 3 shows GPU metrics (not "GPU metrics not available")
- [ ] **PDF Processing:** Tab 1 successfully processes sample PDF
- [ ] **Embeddings Generated:** Tab 1 shows "✅ Generated N embeddings"
- [ ] **Semantic Search:** Tab 2 returns relevant results for "What is the diagnosis?"
- [ ] **Top K Slider:** Changing slider from 3 to 5 returns more results
- [ ] **GPU Metrics Refresh:** Tab 3 refresh button updates metrics
- [ ] **No Console Errors:** Browser console shows no red errors

---

## Sample Questions to Test

Use these queries after processing `sample_medical_note.txt`:

| Question | Expected Result |
|----------|----------------|
| "What is the diagnosis?" | Should return chunk with "Migraña sin aura" |
| "What treatment was prescribed?" | Should return "Ibuprofeno 400mg..." |
| "What were the vital signs?" | Should return "TA: 130/85 mmHg, FC: 78 lpm..." |
| "Who is the doctor?" | Should return "Dr. María González Rodríguez" |
| "What is the prognosis?" | Should return "Favorable. Control en 7 días..." |

---

## Performance Benchmarks

Expected response times (RTX 4090):

| Operation | Time | Notes |
|-----------|------|-------|
| PDF Processing (1 page) | <2s | Includes text extraction + chunking |
| Embedding Generation (3 chunks) | <100ms | GPU-accelerated |
| Semantic Search | <50ms | Includes query embedding + cosine similarity |
| GPU Metrics Refresh | <10ms | Lightweight read operation |

---

## Dependencies

**Core:**
- `gradio>=5.0.0` - Web UI framework
- `PyPDF2>=3.0.0` - PDF text extraction
- `numpy>=1.24.0` - Vector operations

**RAG Service (separate):**
- `fastapi` - API server
- `sentence-transformers` - Embeddings model
- `torch` - GPU acceleration

---

## Advanced Usage

### Custom Chunk Size

Edit `test_rag_ui.py` line 47:
```python
document_chunks = chunk_text(text, chunk_size=500, overlap=50)
#                                     ^^^^^^^^^ Increase for longer chunks
```

**Trade-offs:**
- Larger chunks: More context, fewer chunks, slower search
- Smaller chunks: More precise, more chunks, faster search

---

### Multiple Document Support

Currently supports 1 PDF at a time. To support multiple:

1. Modify `process_pdf()` to append to `document_chunks` instead of replacing
2. Add "Clear Documents" button to reset state
3. Display list of loaded documents in UI

---

## Logs and Debugging

**Gradio Logs:**
```bash
# stdout shows requests and errors
python test_rag_ui.py
# Look for:
# - "Running on http://0.0.0.0:7860"
# - Request logs: "POST /api/search 200"
```

**RAG Service Logs:**
```bash
# In separate terminal where RAG Service runs
tail -f logs/rag_service.log
```

**Browser Console:**
```
F12 → Console tab
# Look for fetch errors or JavaScript exceptions
```

---

## Next Steps

After validating the UI:

1. **Benchmark Performance:** Use `BENCHMARKING.md` guide
2. **Test with Real PDFs:** Upload actual medical notes
3. **Optimize Chunk Size:** Experiment with chunk_size parameter
4. **Evaluate Search Quality:** Compare results with expected answers
5. **Monitor GPU Usage:** Verify GPU is utilized during embeddings

---

**Created:** 2026-01-28
**Status:** ✅ Ready for Testing
