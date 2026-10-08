#!/usr/bin/env bash
# The landing's model (backlog #32), installed ON the droplet. Called by BOTH
# remote-bootstrap.sh (provisioning) and deploy-server.yml (every push), so the
# weights are never a hand-placed file that a re-provision would forget.
# Idempotent: an already-downloaded model is left alone.
set -euo pipefail

VENV="${VENV:-/opt/aire/.venv}"
REPO="${REPO:-/opt/aire}"
MODEL_DIR="${MODEL_DIR:-/opt/aire/models/minilm}"
BASE="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"

"$VENV/bin/pip" install -q --no-input -r "$REPO/server/requirements-nickname.txt"
install -d -m 755 "$MODEL_DIR"

# quint8_avx2, NOT avx512: /proc/cpuinfo on this droplet reports avx2 only, and
# the avx512-quantized graph would fall back to a slow path (verified 2026-08-11).
fetch() {
  local url="$1" dest="$2"
  [[ -s "$dest" ]] && return 0
  echo "    downloading $(basename "$dest")…"
  curl -fsSL "$url" -o "$dest.part" && mv "$dest.part" "$dest"
}

fetch "$BASE/onnx/model_quint8_avx2.onnx" "$MODEL_DIR/model_quint8_avx2.onnx"
fetch "$BASE/tokenizer.json" "$MODEL_DIR/tokenizer.json"
