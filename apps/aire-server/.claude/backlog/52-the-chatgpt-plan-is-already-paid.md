# 52 — The ChatGPT plan is already paid: run OpenAI turns on it through Codex, not on metered tokens

Status: **Proposed 2026-10-26** — box decided the same day: **this Mac**; Codex is never used directly
Proposed: 2026-10-26 by Bernard (*"así como se puede usar Codex y Claude para mí, que también se utilice esta cuenta para no estar utilizando todo el tiempo los tokens de OpenAI y estarme gastándolos cuando ya tengo incluso posibilidad de usar Astra directamente"*).

## What it is

Bernard pays a ChatGPT Pro plan (≈ MXN 2,000/month, the US$100 tier). Codex CLI signed in
with that ChatGPT account runs GPT-6 Astra headlessly on the plan's quota, with no API key
and no per-token bill. Every OpenAI turn that is Bernard's own work should run there first;
metered tokens (Azure OpenAI, #51; `insult-openai`) only when the plan cannot serve it.

## Verified 2026-10-26 (this Mac, $0)

- `codex-cli 0.164.0` (npm `@openai/codex`), `codex login` → `Logged in using ChatGPT`;
  the credential lives in `~/.codex/auth.json`.
- `codex exec -m gpt-6-astra -c model_reasoning_effort="medium" -s read-only
  --skip-git-repo-check --json "<prompt>" </dev/null` answered; the session log
  (`~/.codex/sessions/…jsonl`) records `"model":"gpt-6-astra"`, `"effort":"medium"`.
- One direct run proved it: videopipe's 16 KB script package on stdin, `-o <file>` for the
  reply (script-vidrios.js, 2026-10-26). Then Bernard: *"DESINSTALA CODEX AHORA, y solo debes usar
  el coagente de guion astra, a través de AIRE"* — `codex logout` + `npm uninstall -g @openai/codex`
  the same hour. No consumer calls Codex itself again; the codex binary only lives as AIRE's agent.

## Decided by Bernard 2026-10-26

- **The box is this Mac** (*"backlog para esta mac"*): AIRE spawns the Codex agent here, signed in
  with Bernard's ChatGPT plan; the droplet stays out of it (#49 item 2).
- **Every Astra turn goes through AIRE**, the videopipe script coagent first (GPT-6 Astra Medium,
  its hard rule). Until this card ships, videopipe has no script transport: no Codex direct, and
  scraping chatgpt.com is out on the Terms.

## Why (the money and the terms)

- The ChatGPT subscription includes **no API credit**; the API is billed apart.
  `insult-openai` cost USD 81 in eight days (#51) on tokens the plan could have covered.
- Pro plans have **no five-hour limit** in Codex (weekly limits may apply), per
  learn.chatgpt.com/docs/pricing.
- The ChatGPT Terms of Use (2026-01-01) forbid *"Automatically or programmatically extract
  data or Output"*: scraping chatgpt.com (videopipe's `coagent.mjs`) is the wrong road;
  Codex is OpenAI's own client and the sanctioned one.

## The shape (reuse, not a new door)

`codex` is already one of the agents the ACP backend (#49) can name: a roster entry
`provider: "codex"` in `AIRE_ACP_AGENTS`, bound per session at birth, on a box where
`codex login` holds Bernard's ChatGPT session. No new door, no new ledger row with dollars:
the cost of a plan turn is $0 marginal, so `aire_spend` needs a row shape for "plan quota"
(#49 item 4 already asks for it).

## The decisions that are the owner's

- **Who may use it.** The plan is Bernard's personal account: his own consumers (videopipe,
  og118 for himself, Discord for himself) yes. Reselling it to invited keys (#51's clients)
  is NOT this item: third-party use of a ChatGPT plan is "Sign in with ChatGPT", a limited
  partner trial today (developers.openai.com/siwc/quickstart).
- **Exhaustion signal.** When the weekly limit hits, what Codex emits is not measured; the
  rotor (#31) must learn it before this carries a fleet, or it repeats the
  provider-error-painted-as-text family (AIRE-SUB-DISABLED-1).
- Images: Codex generates with `gpt-image-2` on the same quota (`$imagegen`); whether it
  works inside `codex exec` is not verified.
