# Local Dev Must Match the Deployed Auth Mode — bearer ≠ auth0 is a WHOLE-SHELL swap

`OG118_AUTH_MODE` / `NEXT_PUBLIC_OG118_AUTH_MODE` is **not** a small auth toggle —
it selects a **different rendered application surface**. Running og118 locally in a
mode other than the one staging/prod runs is the fastest way to manufacture a fake
"staging vs localhost diverged" panic and to verify/demo on a shell that isn't the
one that ships.

## The two shells

| Mode | Conversation source | Shell rendered | "Guardado localmente" banner |
|------|---------------------|----------------|------------------------------|
| `auth0` (staging, prod, **and the canonical `.env.local`**) | cloud `RemoteConversationLibrary` (server `/conversations`, per-account) | modern account shell: persona/element selector, cloud Projects, cloud conversations, audio-draft-in-composer, Resonance | **absent** |
| `bearer` (legacy speed-bump, open routes locally) | identity-scoped **IndexedDB** (`--legacy`) | legacy local-first shell — a stripped subset | **present** |

Same commit, same committed `dist/`, same code — the composer/shell still looks
"older" in `bearer` because account-gated surfaces never light up. The divergence
is **runtime config, not code**.

## The rule

1. **Run og118 web locally in `auth0` mode — the config `apps/og118/web/.env.local`
   already ships.** `http://localhost:3000` is a registered Auth0 callback
   (`og118-spa`) precisely so local dev logs in like staging. Just `pnpm --filter
   og118-web dev` and log in; do **not** override `NEXT_PUBLIC_OG118_AUTH_MODE`.
2. **NEVER flip to `bearer` to dodge the Auth0 login** when the goal is to
   verify, screenshot, demo, or compare against staging. The login is a real
   human atom — pay it. Flipping to `bearer` to skip it silently swaps the shell,
   so whatever you "verified" was a **non-canonical surface** (Art. 2 — the
   degraded signal that lies).
3. **`bearer` is legitimate only** for backend-contract work that never touches
   the account shell (curl-ing `/conversations`, `/projects`, `/chat/stream`
   under the synthetic principal) — never for judging how the app *looks*.
4. **The build is identical across environments** (see
   [[committed-dist-artifacts]]): staging CI runs `pnpm --filter og118-web build`
   = `next build` only, consuming the **committed** fi-glass `dist/` — it does NOT
   rebuild fi-glass. So a real staging-vs-local rendering difference is **always**
   config/auth mode or stale local `.next` cache, never "staging shipped newer
   code." Check the mode before theorizing a code divergence.

## How to apply — before declaring a staging/local divergence

```bash
# 1. Same commit? staging deploys on every merge to main.
gh run list --workflow=og118-web-staging.yml --limit 1 --json headSha
git rev-parse HEAD
# 2. Committed dist == src? (no drift)
git log -1 --format=%h -- apps/packages/fi-glass/src
git log -1 --format=%h -- apps/packages/fi-glass/dist
# 3. What mode is localhost actually running? (the usual culprit)
#    staging = auth0; if you launched dev with a bearer override, THAT is the diff.
```

If 1 and 2 agree, the render difference is runtime — relaunch local in `auth0`
and log in, then compare on equal footing.

## Why this rule exists

Registered 2026-07-08. Migrating a ChatGPT chat into og118 as a canary, the agent
launched local og118 with `NEXT_PUBLIC_OG118_AUTH_MODE=bearer` to avoid Bernard's
Auth0 login, then screenshotted the migrated chat and reported it verified.
Bernard, looking at `staging.og118.ai` (auth0), saw a **much more modern
composer/shell** than the localhost screenshot and asked why they diverged and
whether the runbook had been skipped. It had: the canonical local config is
`auth0` (`localhost:3000` is a registered callback), the deployed staging is the
**same commit** with the **same committed dist**, and the only difference was the
agent's `bearer` shortcut — which swapped the entire shell to the legacy
local-first variant. The migration *data* was correct, but the *surface* shown was
not the one that ships. The lesson: match the deployed auth mode locally and pay
the login atom; a convenience-flip of a config mode can silently change the whole
app you think you're verifying. See [[00-constitution]] Art. 2 (verify the real
running surface, never a degraded proxy) + Art. 6 (run the canonical config),
[[committed-dist-artifacts]], and [[framework-first-canary]].
