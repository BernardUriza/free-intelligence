# 32 — The nickname door: a public landing that is a game, and the invite funnel behind it

Status: In progress
Proposed: 2026-08-11 by Bernard

## What it is

AIRE has had no public face at all: `https://aire.bernarduriza.com/` answered `307
→ /login`, and the only unauthenticated bytes in the whole system were two health
JSONs. The landing is now the front door — and Bernard's spec is that it must be a
**game**, not a poster:

1. A visitor types a small piece of text.
2. A **small pretrained model running on the droplet** — no Claude call, no API
   spend — turns that text into a **unique nickname**.
3. The visitor may **alter** the nickname it gave them.
4. A **Request access** button appears.
5. That button emails **Bernard's personal address** a link.
6. Bernard clicking the link **is** the approval: it mints a token bound to that
   nickname.
7. That person can now use AIRE.

The funnel is the point: the fun part (the nickname) is also the identity part. A
stranger leaves the landing already named, and the name is what the token is issued
against.

## The measured constraint that shapes it (2026-08-11)

The droplet is `s-1vcpu-512mb-10gb`, and it is **already tight**:

```
Mem: total 458  used 234  free 19  available 223     Swap: 1023 used 241
/dev/vda1 8.7G used 4.4G (51%)      1 vCPU
```

**223 MB of headroom and one core, with the daemon holding 234 MB.** That kills the
obvious reading of "a HuggingFace model on the droplet":

- PyTorch is out — the wheel alone is ~800 MB on disk and ~250 MB RSS at import.
- A *generative* tiny LM (`distilgpt2` int8 ONNX, ~85 MB file, ~200 MB RSS) does not
  fit beside the daemon without the 1 GB size (+$2/mo, inside the [[do-budget]] cap
  but a spend event that is Bernard's to authorize) — **and it is the wrong tool
  anyway**: distilgpt2 continues English prose; it does not produce handles.
- What fits **today, at $0**: `all-MiniLM-L6-v2` **int8 ONNX (~23 MB file)** under
  `onnxruntime` (~16 MB wheel), ≈130–150 MB RSS steady, ~20 ms per short string on
  one core.

So the design is **embed → nearest neighbours in a curated vocabulary**: the text
becomes a vector, the vector picks its adjective and its noun. Same text always
yields the same nickname (a feature — the name is *derived* from what you wrote),
and semantically close texts yield related names. It is a real pretrained
transformer doing real inference on the droplet, inside the budget, without
touching the daemon's memory.

**It runs as its own systemd unit with `MemoryMax=` set.** If the model ever OOMs it
dies alone; the daemon must not fall with it.

## Canonical path to reuse (Art. 6)

- **Routing**: already done this session — `/` is public and static (`○` in the
  build output, proving it opens no database connection), the console moved to
  `/console`, and a signed-in visitor hitting `/` is redirected there so Bernard
  never pays a click for a page aimed at strangers.
- **The signed link**: `front/lib/session.ts` already does HMAC-SHA-256 over an
  expiry keyed with a secret. The approval link is the same primitive in Python.
- **Where each half runs** — this is forced by the two laws, not chosen:
  the front may not write, so **the daemon mints the token** (it holds the pen) and
  **redirects to the front**, which renders the confirmation. Daemon writes,
  waiter renders, no law bent.
- **The new endpoint, not SSH** ([[ssh-is-a-missing-endpoint]]): the nickname
  service and the approval route are endpoints on the droplet, exposed through the
  existing Caddy at `gate.bernarduriza.com`.

## The decisions that are Bernard's

1. **His personal address.** `~/CLAUDE.md` records `bernarduriza@gmail.com`; this
   session runs as `vegdevida@gmail.com`. Assumed the former — one word from him
   changes it.
2. **The mail transport.** Nothing exists yet: `~/.secrets/` holds no SMTP, Resend,
   Postmark or SendGrid credential. Cheapest paths are Resend's free tier (3 000
   mail/month, an API key) or Gmail SMTP with an app password. Either way it is a
   new secret file + a `provision-do.sh` line ([[device-verb-protocol]]'s
   persistence law: a knob that only lives in a running process is not shipped).
3. **Multi-tenant tokens do not exist yet.** `server/aire/server.py` accepts exactly
   two constants from the environment — `AIRE_AUTH_TOKEN` and `AIRE_CANARY_TOKEN`.
   Issuing a token *per nickname* means a real `aire_token` table and a lookup on
   every request, which is also the natural home for [[28-per-token-budget]]. That
   is the largest slice, and it is where a leaked invite becomes a spend event.

## Slices

| # | Slice | State |
|---|---|---|
| a | Public `/`, console to `/console`, signed-in redirect | **Done 2026-08-11** — build green, `/` static, landing leaks no table name |
| b | The nickname service on the droplet (MiniLM int8 ONNX, own unit, `MemoryMax`) + the landing game UI calling it | In progress |
| c | Request-access → mail to Bernard with an HMAC-signed link | Not started — blocked on decisions 1 & 2 |
| d | Approval mints a per-nickname token (`aire_token`, daemon-side) + the front's confirmation page | Not started — blocked on decision 3 |

## Status / next step

Slice (a) landed. Slice (b) is buildable now with no spend and no open decision.
Slices (c) and (d) each wait on one answer from Bernard above — neither blocks (b).
