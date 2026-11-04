# Free Intelligence

A monorepo for a resident, persistent AI substrate: an agent runtime, a chat framework built on it, and the apps that run on both. The app that ships today is **og118** at https://app.og118.ai.

## What's in here

| Path | What it is | Status |
|------|-----------|--------|
| `apps/og118/web` | og118's Next.js web app | Live at app.og118.ai |
| `apps/og118/server` | og118's FastAPI server over `fi-runner` (SSE turn stream) | Live (Azure Container Apps) |
| `apps/og118-ios` | og118's native iOS client | In development |
| `apps/packages/fi-glass` | The chat framework (React): transcript, composer, agent surfaces | Published, consumed by og118 |
| `apps/packages/fi-runner` | The agent runtime and its stream contract | Published |
| `apps/packages/fi-core` | Python primitives: RAG chunking, stores, task tracker | Published |
| `apps/packages/free-intelligence-core` | TypeScript contracts, reducers and generated schemas | Published |
| `apps/server-bot` | Discord personas and the persona runner | Live |
| `apps/aire-server` | AIRE, the gateway every model call goes through | Live |
| `apps/fi-monitor` | Windows desktop monitor (Tauri) | Built on demand |
| `apps/fenix` | A stationery shop's assistant | Paused |
| `apps/aurity` | The original Next.js frontend. It's the reference shape fi-glass extracts from; it isn't deployed | Reference only |

## Run og118 locally

You need Node 20, pnpm 10 and Python 3.12+.

```bash
pnpm install --frozen-lockfile

# One-time server setup (see apps/og118/server/README.md)
cd apps/og118/server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../packages/fi-runner[claude]
pip install -e "../../packages/fi-core[stores-hdf5]"
cd -

make dev        # server on :8118 + web on :3000
make test       # server pytest + web vitest
make dev-kill   # stop both
```

Put your credentials in `apps/og118/server/.env.local` and `apps/og118/web/.env.local` (both gitignored). Never commit them.

## Contributing

`main` is protected. Every change goes through a pull request that has to pass the PR Gate (types, unit tests, contract checks, the iOS harness) and the AI Gatekeeper. A merge to `main` deploys og118.

## License

[PolyForm Noncommercial 1.0.0](LICENSE). Commercial licensing is available: bernarduriza@gmail.com.
