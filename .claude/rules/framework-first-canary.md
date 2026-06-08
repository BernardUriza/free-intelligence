# Framework-First for Canary-Discovered Capabilities

This rule exists because of **DD-002-LESSON** (2026-06-07). og118 dogfooding
revealed a real pain — the chat had no visible transcript, the user's message
vanished, every turn felt like a brand-new chat. The fix (DD-002A) was
implemented **entirely inside the og118 consumer** (`og118Transcript.ts`,
`useOg118Agent.ts`, `Og118AgentChat.tsx`). The fix worked, but the *way* it was
done was architecturally wrong: a reusable conversation capability got trapped in
the consumer wrapper instead of rising to the framework.

## The principle

**og118 is not only a final app — it is the canary for fi-glass.** When a pain in
og118 reveals a missing *reusable* capability, the change must transcend the
consumer so future apps (slate, paper, the next shell) inherit it. A consumer-local
patch that buries a reusable primitive is debt, even when it passes tests.

Asking "what's the main pain?" is **not** an invitation to apply a paranoid local
patch. It is to find where the framework is failing the real product, and map the
user's pain to the **correct layer of abstraction** (core vs fi-glass vs app).

## Incorrect (do not do this)

- Solve a reusable agentic-conversation need only inside og118.
- Add transcript helpers / conversation composition in the consumer when the
  pattern clearly applies to future apps.
- Treat a dogfooding pain as an isolated app bug without elevating it to the
  framework.
- Optimize for immediate risk when doing so prevents the learning from transcending.

## Correct (do this)

1. When og118 reveals a missing primitive, **classify first**: does it belong in
   `core` (pure types/data/reducers), `fi-glass` (reusable hook/component/surface),
   or the `consumer` (endpoint, token, branding, persona, screen composition)?
2. If it applies to future apps, **implement the primitive in core/fi-glass**.
3. Keep og118 as the **first consumer / canary** of that abstraction.
4. A consumer-local implementation is allowed **only as a temporary prototype**,
   and only with an explicit extraction issue/gate that says it will move to the
   framework.
5. **Do not merge** consumer-local solutions for clearly reusable capabilities
   without a documented justification.

## How to tell "reusable" from "app-specific"

Reusable → belongs in framework: transcript/agent-conversation state, message
folding, optimistic user message, assistant fold on `done`, live-turn rendering,
new-conversation lifecycle, session continuity, chat state, generic surfaces.

App-specific → stays in the consumer: API endpoint/transport, access token & auth
banner, branding/copy, model/persona config, screen-specific layout, the wiring
that hands the transport hook to the framework component.

## Gatekeeper enforcement

The AI gatekeeper (bair, centralized in `BernardUriza/.github`) must flag this
pattern. When an app under `apps/*` adds reusable chat/agent/transcript/
conversation/surface logic **without a corresponding change in fi-glass/core or an
explicit justification**, it must surface:

> "Potential framework abstraction leak: reusable chat/agent conversation logic
> added in consumer app. Move to fi-glass/core or document why this is
> app-specific."

It must NOT block legitimate app-specific work: branding, copy, layout, API
wiring, or tokens.

## Why this rule exists

Saved 2026-06-07 after DD-002A was built consumer-local. The fix shipped and
worked, but Bernard caught that the reusable conversation primitive should live in
fi-glass/core so every future shell inherits it — and that the canary's whole
purpose is to push gaps up into the framework, not to absorb them. See
`[[DD-002-LESSON]]` in `.claude/SESSION_STATE.md`.
