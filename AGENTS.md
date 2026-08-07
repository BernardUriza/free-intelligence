# Agents: read CLAUDE.md

The canonical agent context for this repo is [`CLAUDE.md`](CLAUDE.md) — the
decisions already made, the verified SDK facts, the discarded routes, and the
laws under [`.claude/rules/`](.claude/rules/). This file exists only so tools
that look for `AGENTS.md` find the same source of truth.

Non-negotiables, in one breath (full text in `CLAUDE.md` and the rules):

- **English only** — every committed byte.
- **The daemon never returns HTML** — JSON `/health`, SSE events, and the
  `/v1/*` gateway relay are its only mouths.
- **Write-only toward Postgres** — every human-facing read lives in
  [`front/`](front/) (its own law: `front/.claude/rules/read-only-waiter.md`).
- **Functions ≤30 lines, files ≤150** (`scripts/check_law.py` gates CI).
- **Never drive the daemon over SSH** — a reach for SSH names a missing
  endpoint; build the endpoint.
- **The log is the truth; the view is a cache.**
