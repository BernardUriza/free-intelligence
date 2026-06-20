# og118 server (v0, local-only)

FastAPI + SSE over `fi-runner` (Claude Code backend, OAuth). Emits fi-runner's
native turn stream; the og118 web hook maps it onto fi-glass/core contracts.

## Run locally

```bash
cd apps/og118/server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../packages/fi-runner[claude]
pip install -e "../../packages/fi-core[stores-hdf5]"  # rag_store capability's HDF5 backend

# Auth: Max-subscription OAuth (same token as insult_ai)
export CLAUDE_CODE_OAUTH_TOKEN=...      # provided by Bernard, never committed

uvicorn app:app --port 8118
```

## Smoke test (the v0 step-1 gate)

```bash
curl -N -X POST http://localhost:8118/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"hola"}'
# expect: SSE frames — open / text* / result / done
```

`CLAUDE_CODE_OAUTH_TOKEN` is read from the ambient environment by the
claude-agent-sdk. Never hard-code it. No cloud infra until the local e2e is green.
