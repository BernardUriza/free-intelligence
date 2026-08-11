"""The nickname generator — a real transformer on the droplet, in its own process.

Backlog #32. A visitor to the public landing types a little text; this turns it
into a name. No Claude call, no API spend: `all-MiniLM-L6-v2`, int8-quantized to
ONNX, embedding the text and letting the vector pick its own adjective and noun
out of a curated vocabulary.

**It runs as its own systemd unit, never inside the daemon.** The droplet has
458 MB total and the engine already holds ~234 MB; this process costs ~140 MB.
Its unit carries a `MemoryMax`, so if the model ever bloats it dies alone and the
pen keeps writing. It reads no database and writes none — it is neither waiter
nor pen, just a function with weights.

Three findings from the pre-build browser test (2026-08-11), each of which the
naive version got wrong and all three of which are load-bearing:

1. The droplet is **avx2, without avx512**, so the file is `model_quint8_avx2`.
2. Comparing a sentence against bare words scores ~0.15 and is mostly noise —
   the vocabulary must be lifted into sentence space with a template.
3. Templates alone make a few words hubs ("nocturnal" won for every input);
   **centering** the vocabulary matrix is what fixes it. Measured after: the top
   adjective was distinct for 10 of 10 sample texts, at 48 ms each.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from tokenizers import Tokenizer

from .bearer import ACCEPTED_TOKENS, accepted, presented_token

MODEL_DIR = Path(os.environ.get("AIRE_MODEL_DIR", "/opt/aire/models/minilm"))
VOCAB = json.loads((Path(__file__).parent / "nickname_vocab.json").read_text("utf-8"))
TEMPLATE = {
    "adjective": "someone whose character feels {}",
    "noun": "someone whose spirit animal or trade is the {}",
}
MAX_CHARS = 400

_state: dict[str, object] = {}


def _embed(texts: list[str]) -> np.ndarray:
    """Mean-pool the last hidden state under the attention mask, then L2-normalise
    — the pooling `sentence-transformers` itself applies for this model."""
    tokenizer: Tokenizer = _state["tokenizer"]  # type: ignore[assignment]
    session: ort.InferenceSession = _state["session"]  # type: ignore[assignment]
    encodings = tokenizer.encode_batch(texts)
    ids = np.array([e.ids for e in encodings], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    feed = {"input_ids": ids, "attention_mask": mask}
    if any(i.name == "token_type_ids" for i in session.get_inputs()):
        feed["token_type_ids"] = np.zeros_like(ids)
    hidden = session.run(["last_hidden_state"], feed)[0]
    weights = mask[..., None].astype(np.float32)
    pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
    return pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9, None)


def _centered(matrix: np.ndarray) -> np.ndarray:
    """Subtract the vocabulary's own centroid. Without this a handful of words sit
    nearest the centre of the space and win for every input (measured)."""
    shifted = matrix - matrix.mean(axis=0, keepdims=True)
    return shifted / np.clip(np.linalg.norm(shifted, axis=1, keepdims=True), 1e-9, None)


def _single_threaded() -> ort.SessionOptions:
    """One vCPU. Letting onnxruntime spawn a thread pool on a box this size costs
    memory and buys nothing."""
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    return options


def load() -> None:
    """Weights and vocabulary, once, at startup — so the unit is only `ok` when it
    can actually answer, and no visitor pays the four seconds."""
    tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=256)
    tokenizer.enable_padding()
    _state["tokenizer"] = tokenizer
    _state["session"] = ort.InferenceSession(
        str(MODEL_DIR / "model_quint8_avx2.onnx"),
        providers=["CPUExecutionProvider"],
        sess_options=_single_threaded(),
    )
    for part, words in VOCAB.items():
        _state[part] = _centered(_embed([TEMPLATE[part].format(w) for w in words]))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load()
    yield
    _state.clear()


app = FastAPI(
    title="AIRE nickname",
    description="A small model that names strangers",
    lifespan=lifespan,
)


def _name(text: str) -> dict[str, str]:
    vector = _embed([text])[0]
    picked = {
        part: VOCAB[part][int(np.argmax(np.asarray(_state[part]) @ vector))] for part in VOCAB
    }
    return {**picked, "nickname": f"{picked['adjective']} {picked['noun']}"}


@app.get("/health")
def health() -> JSONResponse:
    ready = "session" in _state
    body = {"status": "ok" if ready else "loading", "vocabulary": len(VOCAB["noun"])}
    return JSONResponse(body, status_code=200 if ready else 503)


@app.post("/nickname")
async def nickname(request: Request) -> JSONResponse:
    if not ACCEPTED_TOKENS:
        return JSONResponse({"detail": "no token is configured"}, status_code=503)
    if not accepted(presented_token(request)):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if "session" not in _state:
        return JSONResponse({"detail": "the model is still loading"}, status_code=503)
    text = str((await request.json()).get("text", "")).strip()[:MAX_CHARS]
    if not text:
        return JSONResponse({"detail": "say something first"}, status_code=400)
    return JSONResponse(_name(text))
