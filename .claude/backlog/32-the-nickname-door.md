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

1. ~~**His personal address.**~~ **Resolved 2026-08-11:** `bernarduriza@gmail.com`,
   the address `~/CLAUDE.md` records. Lives in `~/.secrets/aire-access.txt`.
2. ~~**The mail transport.**~~ **Resolved 2026-08-11: Resend.** The reason is
   specific, not a preference — its free tier mails the account's OWN address with
   no verified domain and no DNS records, and the only recipient this system ever
   has is Bernard. A Gmail app password would also have worked and was rejected: it
   is a credential to his whole mailbox, where this is a sending-only key revocable
   without touching anything else. He already had a three-year-old Resend account
   with two keys whose values were never saved, so a THIRD key (`aire-invitations`,
   sending access only) was created rather than regenerating one — regeneration
   would have invalidated whatever the old ones feed ([[secrets-management]]).
   Homes: `~/.secrets/resend-aire.txt`, restored by `infra/lib/secrets.sh`.
3. **Multi-tenant tokens do not exist yet.** `server/aire/server.py` accepts exactly
   two constants from the environment — `AIRE_AUTH_TOKEN` and `AIRE_CANARY_TOKEN`.
   Issuing a token *per nickname* means a real `aire_token` table and a lookup on
   every request, which is also the natural home for [[28-per-token-budget]]. That
   is the largest slice, and it is where a leaked invite becomes a spend event.

## Slices

| # | Slice | State |
|---|---|---|
| a | Public `/`, console to `/console`, signed-in redirect | **Done 2026-08-11** — build green, `/` static, landing leaks no table name |
| b | The nickname service on the droplet (MiniLM int8 ONNX, own unit, `MemoryMax`) + the landing game UI calling it | **Done 2026-08-11** — verified E2E through the real browser on the friendly domain |
| c | Request-access → mail to Bernard with an HMAC-signed link | **Done 2026-08-11** — decisions 1 & 2 resolved below; smoke test landed in the real inbox |
| d | Approval mints a per-nickname token (`aire_token`, daemon-side) + the door accepts it | Not started — blocked on decision 3 |

## Slice (b), as measured live (2026-08-11)

Not "it should work" — what was observed:

- `aire-nickname.service` **active**, holding **88.9 MiB** against its `MemoryMax=200M`
  (the estimate was ~140 MB; it came in lighter), with the engine and listener
  untouched beside it.
- `POST https://gate.bernarduriza.com/nickname` from **outside** the droplet:
  **401 without a token**, real names with one.
- In Chrome on **https://aire.bernarduriza.com** (the friendly domain, not the
  Azure hostname): typed a sentence about repairing antique clocks → **"midnight
  almanac"**, then edited it in place to "midnight almanac the second". The whole
  loop a stranger will walk.
- Gates intact after the move: `/` → 200 anonymous, `/console` → 307 to `/login`,
  `/api/nickname` → 405 on GET.

**One honest miss.** Expanding the vocabulary from the 40+40 that was browser-tested
to 60+60 shifted the centroid — centering is vocabulary-dependent — and "soy contador
y odio mi trabajo", which produced *clerical pelican* in the test, now produces
*pedal velodrome*. Four of five samples still land; that one regressed. The lever is
the word list, and the word list is Bernard's taste to set.

## Slice (c), as measured live (2026-08-11)

The whole path walked in the real browser, one stranger's worth:

- Typed *"I run a tiny bakery and I get up at four in the morning to start the
  ovens"* → **hungry foundry**. Edited it to *"the four-o-clock hungry foundry"* and
  pressed **request access**.
- The mail landed in the real Gmail inbox at **6:23 PM**, subject *"AIRE — the
  four-o-clock hungry foundry wants in"* — carrying the **edited** name, which is
  the point: the name is the visitor's, not the model's.
- Clicking the link in the mail redirected to
  `/approved?n=the four-o-clock hungry foundry`, and the row came back from Postgres
  read as **`aire_reader`** with `approved = t` — so the table was created as role
  `aire` and the DDL rule held.
- A **tampered signature** (`?n=impostor&t=…deadbeef`) redirected to `?bad=1` and
  approved nothing.

The transport was smoke-tested before being wired, and the check that mattered was
his inbox, not Resend's `200` — an API accepting a message is not a message
delivered.

## Status / next step

Slices (a), (b) and (c) are live. Slice (d) — the per-nickname token and the door
that accepts it — is the only one left, and it is where a leaked invitation becomes
a spend event, so it is also [[28-per-token-budget]]'s natural home.

The vocabulary stays the open craft question: it is what gives the game its
register, and it is Bernard's taste, not an engineering decision.
