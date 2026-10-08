# The bridge — the droplet's terminal, mirrored to the browser

Status: Dropped 2026-07-20 — superseded by Bernard's own conclusion the same day
Proposed: 2026-07-20 by Bernard

## What it is

A third monorepo half, `bridge/`: a minimal Go service (gotty/ttyd family) that
spawns a command on a PTY (htop, `tail -f aire.log`, the tmux'd Claude Code
TUI), reads its output byte-by-byte, and broadcasts it over WebSocket to an
xterm.js page. The window into the droplet's terminal — the browser evolution
of the "see it like htop over SSH" experience.

Neither pen nor waiter: the bridge never touches Postgres. It does serve HTML —
legal, because the no-HTML law binds the DAEMON (`server/`), not sibling
surfaces.

## Canonical path to reuse (Art. 6)

`ttyd`/`gotty` are the finished canon — if the goal were only the result,
`apt install ttyd` ends this in 10 minutes. Building our own is justified by
exactly two things: (a) **read-only by construction** — no stdin path wired at
all, so a remote shell is impossible by design, not by flag (the port-open
droplet deserves that); (b) the droplet is Bernard's Linux/Go curriculum and
PTY→WS→VT100 is the lesson. Libraries: `creack/pty`, `gorilla/websocket`,
xterm.js.

## The decision that's the owner's

1. Build-for-learning vs adopt ttyd (see above) — Bernard weighs the lesson.
2. Internet exposure: v1 binds `127.0.0.1` only (view via
   `ssh -L 7681:localhost:7681`); opening the port to the world + its auth
   (token/Basic) is a separate, explicit call.
3. What the PTY runs first: htop, the log tail, or the Claude Code tmux.

## Status / next step

Not started. Next: scaffold `bridge/` (Go, thirty-line law applies), systemd
unit + path-filtered deploy, verify through the SSH tunnel on the real droplet.

## Why dropped (2026-07-20, Bernard's call)

*"Si debe ser solo lectura, lo podemos cablear de otra forma, no directa, usando
la base de datos como debe ser… en vez de una conexión al droplet, mejor
conectarme a la base de datos en una nueva tabla, diferente a la de los logs,
donde se reconstruya el transcript completo de Claude Code."* The bridge was a
window into a mortal body's screen; the right wiring is the house theorem — the
transcript lives deathless in Postgres and every view reads the database
(read-only-waiter). The LIVE terminal, when wanted, is direct SSH (the htop
ritual). This is backlog #17 — the conclusion moved there.
