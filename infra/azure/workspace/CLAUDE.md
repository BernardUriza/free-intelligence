# Workspace — Insult Agent Runtime

Postgres is the source of truth. This directory is a periodic projection
(~60s lag). You are read-only here; persistence happens via the
`[REMEMBER: <fact>]` marker in your reply (parsed by the host), NEVER by
writing files in this directory.

## Layout

- `facts/{user_id}.md` — accumulated user_facts. Read before claiming you
  know (or don't know) something about a user.
- `messages/{channel_id}.md` — last ~50 messages per channel. Read on
  cross-channel references ("acuérdate de lo de #philo").
- `disclosure_log.md` — recent disclosure_log rows (vulnerability flags,
  fact reveals). Consult before responding to acute emotional content.

## Hard Rules

- DO NOT call `Write`, `Edit`, or `Bash`. Only `Read`, `Grep`, `Glob` are
  available — using anything else means you misread the available tool set.
- DO NOT grep the whole workspace "for context". Read the file named after
  the user_id or channel_id the host gave you in the framing. Anything
  else is a waste of tokens.
- DO NOT invent user_ids or channel_ids. The host always injects them.
- DO trust the live conversation over the projection if they disagree —
  the 60s lag is real.
