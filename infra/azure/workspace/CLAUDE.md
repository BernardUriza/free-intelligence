# Workspace — Insult Agent Runtime

Postgres is the source of truth. Persistence happens via the
`[REMEMBER: <fact>]` marker in your reply (parsed by the host), NEVER by
writing files in this directory.

## Preferred path: direct Postgres tools (F4, v3.9.51+)

The host registers five in-process MCP tools that query Postgres directly.
**Use these first** — they return live data (zero staleness) and the
structured output is easier to read than the markdown projection:

| Need | Tool |
|---|---|
| What do I know about user X? | `mcp__insult_db__get_user_facts(user_id)` |
| What was just said in this channel? | `mcp__insult_db__get_recent_messages(channel_id, limit)` |
| Did the user mention "X" earlier? | `mcp__insult_db__search_messages(channel_id, query, limit)` |
| Has the user disclosed anything clinical? | `mcp__insult_db__get_disclosure_log(user_id, days)` |
| What is the user's emotional arc state? | `mcp__insult_db__get_emotional_arc(user_id, channel_id)` |

The `user_id` and `channel_id` are always injected by the host in the
`<turn_context>` block at the top of your prompt. Do not invent them.

## Fallback: markdown projection (legacy, being decommissioned)

This directory is the older periodic projection (~60 s lag). It still
exists during the F4 phase-1→phase-3 transition. Prefer the MCP tools
above unless you have a specific reason — and never `Grep` the whole
workspace "for context".

- `facts/{user_id}.md` — same data as `get_user_facts`
- `messages/{channel_id}.md` — same data as `get_recent_messages`
- `disclosure_log.md` — same data as `get_disclosure_log` (no user_id
  filter — the markdown version is global)

## Hard Rules

- DO NOT call `Write`, `Edit`, or `Bash`. Only `Read`, `Grep`, `Glob`
  and the `mcp__insult_db__*` tools are available — using anything else
  means you misread the available tool set.
- DO NOT grep the whole workspace "for context". Hit the specific tool
  with the specific user_id / channel_id the host injected.
- DO NOT invent user_ids or channel_ids. The host always injects them.
- DO trust the live conversation over either the projection or the tool
  output if they disagree — your most recent message context wins.
