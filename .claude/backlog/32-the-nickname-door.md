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
3. ~~**Multi-tenant tokens do not exist yet.**~~ **Resolved 2026-08-11**, and with
   it [[28-per-token-budget]]. `aire_token` holds one row per nickname — hash only,
   never the plaintext — with its own `budget_usd`/`spent_usd`. Bernard's answer to
   the delivery question was the one that stores least: **no email is ever asked of
   the visitor.** They leave a name; the key goes to Bernard and he hands it over.
   No stranger's contact in the database, no second mail path.

## Slices

| # | Slice | State |
|---|---|---|
| a | Public `/`, console to `/console`, signed-in redirect | **Done 2026-08-11** — build green, `/` static, landing leaks no table name |
| b | The nickname service on the droplet (MiniLM int8 ONNX, own unit, `MemoryMax`) + the landing game UI calling it | **Done 2026-08-11** — verified E2E through the real browser on the friendly domain |
| c | Request-access → mail to Bernard with an HMAC-signed link | **Done 2026-08-11** — decisions 1 & 2 resolved below; smoke test landed in the real inbox |
| d | Approval mints a per-nickname token (`aire_token`, daemon-side) + the door accepts it | **Done 2026-08-11** — the ceiling shipped blind and did not bite; fixed and measured biting at `8d9e5f3` |

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

## Slice (d), as measured live (2026-08-11) — it shipped BLIND

The code for (d) landed at `a359224` and was reported as shipped. It was not: the
ceiling could not bite, and nothing said so. One stranger's walk found it.

**The walk.** Typed *"I spend my nights fixing other people's databases and my
mornings drinking cold coffee"* → **drowsy almanac**. Requested access; the mail
landed at 8:10 PM; clicking the link in the inbox redirected to `/approved`, which
correctly refuses to print the key. The key arrived in a second mail, hash-only in
the database, with its revoke link beside it.

**Then the door was actually used, and the ceiling was a decoration.** Two real
turns at **$0.108** and **$0.116** against a **$0.05** ceiling left
`spent_usd = 0`. Two defects, each silent by construction:

1. **`turn_cost` read the wrong shape.** It reached for the SDK dataclass's
   `.usage`; the HTTP surface hands it the flattened dict. `getattr(dict, "usage")`
   is `None`, so every turn cost **$0.00**. Same family as the #23 budget lie and
   the #31 exhausted-pool lie: a money function that answers 0 to a shape it does
   not recognise is indistinguishable from a free turn. It now reads both shapes,
   is pinned by `tests/test_turn_cost.py`, and a real result that banks nothing
   PRINTS instead of passing quietly.
2. **`background: true` never billed at all.** The detached runner (#22a) had no
   way to report its dollars, so one flag in the request body bought a capped key
   unlimited spend. `launch_detached` now takes a `CostSink` — the engine reports
   a number and never learns whose ceiling it feeds.

**Verified biting after `8d9e5f3`**, on the same key, from outside the droplet:
a streaming turn banked `$0.0068607`; a `background: true` turn banked its own
dollars (spend jumped to `$0.04352` with no socket attached); the next turn
crossed the ceiling at `$0.07152` and the one after answered
**`402 token_budget_spent`**. Clicking the revoke link in the mail then made the
same key answer **401**, with `revoked_at` set.

**One honest caveat, by design:** a turn is banked when its `result` arrives, so a
key always overshoots by its last turn — $0.0715 landed against a $0.05 ceiling.
The cost is unknowable before the turn runs; the ceiling refuses the NEXT one. A
small ceiling with an expensive first turn (a cold cache costs ~$0.108) can double
its allowance once.

## Slice (e), the consumer — the fork Bernard resolved 2026-08-11

Verifying (d) surfaced the real gap: **an invited key fitted no lock.** It was
accepted on the message, artifacts and init endpoints — reachable by `curl` and
by nothing else — while the door a real client uses, the gateway (`/v1/*`, #30),
skipped the invited-key check entirely because it is auth-pass-through. His call,
verbatim: *"haz que /v1/* acepte la llave de invitado y que AIRE ponga su
credencial hasta el techo de esa llave."*

**Pass-through remains the default.** A caller carrying their own Anthropic
credential is relayed untouched and AIRE spends nothing on them (pinned by a
test). Only an invited key — which has no credential by construction — is served
with AIRE's own.

Three things it needed, none guessable from the code alone:

1. **`lending.py`, the terms of the loan.** An OAuth token is presented as
   `Authorization: Bearer` AND requires `anthropic-beta: oauth-2025-04-20` —
   `/v1/messages` refuses it without the beta. The caller's own betas are
   APPENDED to, never replaced: the gateway's law is that beta headers forward
   verbatim, and an allowlist there breaks clients as they ship new betas.
2. **`pricing.py` + `prices.json`.** Anthropic reports TOKENS; a ceiling needs
   dollars — the engine's door never needed this because the SDK hands it
   `total_cost_usd` already computed. Cache is priced by TTL (1h write ×2, 5m
   ×1.25, read ×0.1). Two biases toward not overspending: an unrecognised model
   is charged at the DEAREST rate in the table, and list prices are used even
   where an introductory discount is live.
3. **A concurrency slot per key.** The ceiling banks when a turn ENDS, so N
   sockets opened together would all pass the gate before any of them paid — a
   leaked invitation could spend N× its ceiling. `AIRE_INVITE_CONCURRENCY`
   (default 2) joins provisioning so the limit survives a kill test.

**Verified live at `802755b` on the real client**, not on a proxy:

```
ANTHROPIC_BASE_URL=https://gate.bernarduriza.com \
ANTHROPIC_AUTH_TOKEN=<invite key>  claude -p "…"   →  "the door works"
```

That turn banked **$0.094235** against a **$0.05** ceiling; the next request
answered **402 `AIRE: drowsy almanac has spent its budget`** — on the gateway AND
on the engine door. A caller with their own credential was relayed with headers
untouched. After the revoke link the key answers 401, and that 401 comes from
**Anthropic, not AIRE**: an unrecognised key falls back to pass-through and
upstream judges it.

**The operational finding that matters more than the code:** one cold Claude Code
turn costs ~$0.09, because its system prompt and tool schemas are the payload. An
invite ceiling below ~$0.20 is therefore decoration — the first turn alone blows
through it and the ceiling only refuses the second. Set `AIRE_INVITE_BUDGET_USD`
well above one cold turn.

## The credential decision — resolved 2026-08-11

*"pon el de oauth en AIRE."* There is exactly one OAuth token per account
(`~/.secrets/claude-max-oauth.txt` is the SSOT and already listed the AIRE
droplet among its consumers), so this was never a second seat — it was choosing
which credential AIRE hands to strangers, and choosing it explicitly.

`lending.credential()` had been reading `CLAUDE_CODE_OAUTH_TOKEN` — **the
engine's variable** — which made the most sensitive configuration in the system
a side effect of what happened to be in the daemon's environment. It now reads
**`AIRE_LEND_OAUTH_TOKEN`** (or `AIRE_LEND_API_KEY` when a metered key exists),
derived in `compose_env` from the same file the rotator writes, so
`rotate-claude-oauth.sh` keeps working and a kill test restores both slots. Same
value today; three things gained: lending can be switched off without touching
the engine, a metered key can replace it without touching the engine, and no
unrelated credential can silently become what AIRE lends. It is the reasoning
that already gave the Azure front its own `AIRE_CANARY_TOKEN`.

**Verified at `c80690a`:** the process sees both slots, `AIRE_LEND_OAUTH_TOKEN`
and `CLAUDE_CODE_OAUTH_TOKEN` hold the same hash, and an invited key relayed
through the gateway answered *"the slot works"* — banking **$0.000044** for
14 in / 6 out tokens on Haiku, which is exactly `14×$1/M + 6×$5/M`. The price
table matches real Anthropic usage to the cent's eighth decimal.

## What is still open, and it is Bernard's

The slot is chosen; **what fills it** carries two costs worth revisiting:

- **Coupling:** an invited key burning the weekly pool starves the engine. That
  is the failure [[31-credential-failover]]'s rotor exists to survive, now
  reachable by a stranger instead of only by Bernard's own work.
- **Terms:** serving third parties from a personal subscription is plausibly
  outside Anthropic's consumer terms. A metered API key minted for AIRE is the
  clean path, costs nothing until used, and `AIRE_LEND_API_KEY` is already wired
  end to end — drop the value in `~/.secrets/aire-lend-api-key.txt`, re-run
  `compose_env`, and lending switches with no code change (the same atom #31
  is waiting on). Fénix's key was deliberately NOT reused: a credential is
  deployed only where Bernard said it goes.

The vocabulary stays the open craft question: it is what gives the game its
register, and it is Bernard's taste, not an engineering decision.
