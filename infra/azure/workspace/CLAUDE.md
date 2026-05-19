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

## The markdown projection is FROZEN (F4 phase 3, v3.9.56)

The `facts/`, `messages/` and `disclosure_log.md` files you may see in
this directory are **stale leftovers** from before F4. The renderer
that updated them every 60s was decommissioned. `Read`, `Grep`, `Glob`
have been removed from your `allowed_tools`. Use the MCP tools above
for all state queries — the markdown will lie to you.

The only file here that is still authoritative is `CLAUDE.md` (this
file). It is your operating contract, not data.

## Hard Rules

- ONLY the `mcp__insult_db__*` tools are available. Calls to `Read`,
  `Grep`, `Glob`, `Write`, `Edit`, `Bash` will be denied.
- DO NOT invent user_ids or channel_ids. The host always injects them
  in the `<turn_context>` block at the top of your prompt.
- DO trust the live conversation over the tool output if they disagree
  — your most recent message context wins.
