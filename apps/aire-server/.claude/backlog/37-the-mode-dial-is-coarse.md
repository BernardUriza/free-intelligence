# The mode dial is coarse — you cannot ask for WebSearch without also getting the file tools

Status: **Proposed**
Proposed: 2026-08-22 by Claude (surfaced closing fi PR #414's documented cost:
Fénix's cibercafé tutor lost «busca en internet» on the AIRE route, and the
only way to give it back was to hand the tutor Read/Write/Glob/Grep too)

## What it is

`server/aire/engine/options.py` exposes the turn's capability surface as a
**two-notch dial**, and each notch is a closed package:

| `mode` | `allowed_tools` | `disallowed_tools` | `permission_mode` |
|---|---|---|---|
| `complete` | *(none)* | Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch | `default` |
| `agent` | Read, Write, Glob, Grep, WebSearch, WebFetch | Bash | `acceptEdits` |

Registry tools a turn names in `tools:[…]` are unioned into `allowed_tools`
either way (`_mount_tools`, since `5ae8e33`), so the **registry** is already
fine-grained. The **builtins** are not: they move only as a block.

So a caller whose product needs exactly one builtin has no way to say so. The
concrete case that raised this — a homework tutor for children at a cybercafé,
whose persona is half "look it up and cite the source" — needs `WebSearch` and
`WebFetch` and nothing else. Asking for them means also being handed `Read`,
`Write`, `Glob` and `Grep`.

**This is not a hole, and the sky is not falling.** The cage (#24) confines
every file tool to that chat's casita — a scratch directory on the droplet —
and `Bash` is refused in both notches. The tutor's grant is real but small: it
can write and re-read its own notes inside its own casita. What is wrong is
that the grant is **unaskable-for**: the consumer cannot express least
privilege, so the door gives it more than it wants and the consumer documents
the surplus instead of declining it. Least privilege that can only be achieved
by accident is not a policy.

Two smaller things the same fix would settle:

- **`permission_mode` rides the notch too.** Wanting WebSearch drags in
  `acceptEdits`, which auto-approves edits nobody asked for. The cage is what
  makes that survivable, not the mode.
- **`tool_policy` is the one input `AIREBackend` still refuses to forward** —
  it logs a warning saying "AIRE configures tools server-side" (see
  `fi_runner/backends/aire.py::_warn_unenforceable`). A per-turn builtin list
  is exactly the field that would let that warning die.

## Canonical path to reuse (Art. 6)

Do **not** invent a permissions language. Everything needed already exists in
this repo, one layer apart:

- **`TurnSpec` + the door's validation** (`engine/contract.py`, `gateway`'s
  422 discipline) is where a new per-turn field is declared and rejected when
  malformed — the same shape `tools:[…]` took in #29. An allowlist of builtin
  names validated against the union of both notches keeps the surface closed
  by construction; anything outside it 422s, exactly like a registry name the
  door does not ship.
- **`MODES` stays the coarse default.** The named notches are a good default
  and must keep working byte-identically for every caller that names no
  builtins — the fine-grained field is a *narrowing* of the chosen notch, never
  a widening. `agent` + `builtins:["WebSearch","WebFetch"]` should yield the
  agent notch minus the file tools; `complete` + a builtin request should stay
  refused, so the dial never becomes a way to smuggle tools into the mode that
  promises none.
- **`_mount_tools`** already demonstrates the union step where the final
  `allowed_tools` is assembled — the narrowing belongs in the same place, so
  there is one line that decides the turn's surface.
- **The cage (`engine/cage.py`) does not change.** It is the backstop that
  makes a wrong grant survivable and it must keep running regardless of how the
  surface is chosen.

The consumer end is already built and needs nothing: `AIREBackend` takes
`default_mode` per instance (`fi_runner/backends/aire.py`), and og118's
`build_runner(aire_mode=…)` is the seam a consumer sets it through — Fénix's
tutor is its first user.

## The decision that's the owner's

1. **Whether the dial should grow at all.** A defensible answer is no: two
   notches plus the cage plus a Bash ban is a small, auditable surface, and
   every knob added to a security dial is a knob someone can turn wrong. The
   cost of "no" is that consumers keep over-receiving and documenting it.
2. **The shape, if yes** — a narrowing `builtins:[…]` list on the turn (the
   proposal above), versus a third named notch (e.g. `research` = WebSearch +
   WebFetch only) that keeps the door's vocabulary closed and needs no
   validation of caller-supplied names. The third notch is smaller and less
   expressive; the list is general and needs an allowlist.
3. **Whether `permission_mode` follows the builtins or stays welded to the
   notch.** A `research` notch would want `default`, not `acceptEdits`.

## Status / next step

Not built. Nothing is broken today — the tutor works, the cage holds, and fi
PR #414's successor documents the surplus grant plainly in
`apps/fenix/DEPLOY.md` instead of hiding it. This item exists so the surplus is
a **named** debt with an owner's decision attached, not a paragraph someone
rediscovers.

Unblocked by: Bernard picking (1) and, if yes, the shape in (2). If the answer
is no, this item gets **Dropped** with that reasoning recorded — which is a
perfectly good outcome and the one the security posture may well deserve.

See also [#24](24-the-casita-is-not-a-cage.md) (the cage that makes the coarse
grant survivable), [#29](29-grow-the-door-per-turn.md) (the per-turn fields the
door already grew, and the pattern to copy) and
[#35](35-the-consumer-map.md) (the fleet migration that keeps meeting this dial).

## What the coarse dial costs the CALLER — measured 2026-09-09 (free-intelligence)

The founding cost was Fénix's tutor losing web search. Two more landed, and both
are downstream of this same item — the door has no field for a per-turn tool
posture, so a caller cannot express one:

- **fi-runner's `ToolPolicy.companion()` now has ZERO live consumers.** It ships,
  it is tested, and nothing calls it outside its own tests: og118 sends a bare
  `ToolPolicy()` because `companion()` would cross no wire. A framework profile
  that cannot reach the runtime is documentation, not a lock.
- **That gap became a false written guarantee in a repo with real users.** Four
  files in `apps/fenix` stated *"`ToolPolicy.companion()` blocks Bash, Write and
  Edit"* as the reason the server — not the model — generates the .xlsx and the
  tutoring PDF. Wrong twice: the call never happens, and Fénix's tutor runs
  `aire_mode="agent"`, where `Write` IS granted (confined by `engine/cage.py`,
  not by any caller policy). Corrected the same day; the design was right, the
  stated reason was false.
- **The honest stopgap shipped on the fi-runner side:** `_warn_unenforceable` now
  also fires on `builtin_disallowed`, which is exactly the shape `companion()`
  produces — a denylist under the default permission mode used to cross in
  silence. Warned, never silently honoured, until this item lands.

So #37 is not only "a coarse dial": it is the reason a caller's security posture
is unrepresentable. When the door grows per-turn tools, `ToolPolicy` is the
caller-side contract already waiting for it — see free-intelligence
`.claude/backlog/fi-runner-toolpolicy-1-companion-profile.md` and
`fi-runner-aire-backend.md`.

**Second, unrelated finding from the same session, worth a look:**
`engine/options.py:11` still says the real filesystem confinement *"is
`SandboxSettings`, not yet in place — `cwd` is NOT a cage."* That line predates
`engine/cage.py`, which IS the cage (a `PreToolUse` hook denying any file tool
outside the casita). Backlog #24 is the item; the comment is stale either way.
