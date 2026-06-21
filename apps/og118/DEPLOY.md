# og118 — Deploy (Gate 2 CI/CD)

Reproducible deploy via GitHub Actions. Two path-filtered workflows fire on
`push: main`:

- `.github/workflows/og118-backend.yml` → builds `linux/amd64`, pushes to ACR,
  creates/updates the Azure Container App.
- `.github/workflows/og118-web-staging.yml` → builds the Next static export,
  deploys to a **new, temporary staging** Static Web App (NOT og118.ai).

AURITY's `deploy-azure.yml` is untouched. og118.ai / `og118-landing.yml` are
untouched (public cutover = Gate 4).

---

## One-time bootstrap (manual — Bernard runs this once; do NOT commit secrets)

### 1. OIDC federated identity (NOT the shared AURITY `AZURE_CREDENTIALS`)

Create an app registration (or user-assigned managed identity) for og118 and add
a **federated credential** with this exact subject:

```
repo:BernardUriza/free-intelligence:ref:refs/heads/main
```

(Issuer `https://token.actions.githubusercontent.com`, audience
`api://AzureADTokenExchange`.) This lets the `main` workflows log in with no
long-lived secret.

### 2. Azure roles (minimum sufficient)

Grant the federated identity, **scoped to `og118-rg` only**:

- **Owner on `og118-rg`** — recommended. Owner (vs plain Contributor) is needed
  so the workflow can assign **AcrPull** to the Container App's system-assigned
  managed identity (`--registry-identity system`), keeping image pull
  credential-free. Scoped to the throwaway `og118-rg`, Owner is acceptable.
- Alternative (more locked-down): Contributor on `og118-rg` + a pre-created
  AcrPull assignment for the app's MI — but that needs User Access Admin once.

### 3. GitHub secrets (Settings → Secrets → Actions)

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | the federated app/identity client id |
| `AZURE_TENANT_ID` | tenant id |
| `AZURE_SUBSCRIPTION_ID` | `d61ba6bc-eda9-4327-a264-5cfddef30bc8` |
| `OG118_ANTHROPIC_API_KEY` | og118's Anthropic API key (NOT the existing `ANTHROPIC_API_KEY`, whose purpose differs) |
| `OG118_ACCESS_TOKEN` | the bearer value `/chat/stream` requires |
| `AZURE_SWA_TOKEN_OG118_STAGING` | deploy token of the NEW staging SWA (step 5) |
| `OG118_TTS_API_KEY` | Azure OpenAI key for TTS (B3-VOICE-BACKEND-1). **Optional** — unset → `/tts/synthesize` returns 503, deploy stays green |
| `OG118_STT_API_KEY` | Azure OpenAI key for STT/Whisper (B3-VOICE-BACKEND-2 / -STT-CONFIG-1). **Optional** — unset → `/stt/transcribe` returns 503, deploy stays green |

### 4. GitHub variables (Settings → Variables → Actions)

| Variable | Suggested value |
|---|---|
| `OG118_RESOURCE_GROUP` | `og118-rg` |
| `OG118_LOCATION` | `eastus2` |
| `OG118_ACR_NAME` | `og118acr` (globally-unique; adjust if taken) |
| `OG118_CONTAINERAPP_ENV` | `og118-env` |
| `OG118_API_NAME` | `og118-api` |
| `OG118_ALLOWED_ORIGINS` | `https://<staging-swa-host>` (set after step 5) |
| `OG118_MODEL` | `claude-sonnet-4-5` (optional) |
| `OG118_API_URL` | `https://<backend-fqdn>` (set after first backend deploy) |
| `OG118_TTS_ENDPOINT` | Azure OpenAI endpoint base, e.g. `https://<res>.openai.azure.com` (TTS; optional) |
| `OG118_TTS_DEPLOYMENT` | TTS deployment name, e.g. `tts-hd` (TTS; optional) |
| `OG118_TTS_API_VERSION` | default `2025-03-01-preview` (TTS; optional) |
| `OG118_TTS_VOICE` | default `nova` (TTS; optional) |
| `OG118_STT_ENDPOINT` | Azure OpenAI endpoint base for STT/Whisper, e.g. `https://northcentralus.api.cognitive.microsoft.com` (STT; optional) |
| `OG118_STT_DEPLOYMENT` | Whisper deployment name, e.g. `whisper` (STT; optional) |
| `OG118_STT_API_VERSION` | default `2024-06-01` (STT; optional) |

> **TTS (B3-VOICE-BACKEND-1) is opt-in.** Leave `OG118_TTS_*` unset and the
> backend behaves exactly as before — `/tts/synthesize` returns a clean `503
> TTS_NOT_CONFIGURED` and the deploy's TTS-wiring step is a no-op. Set the secret
> + the four vars above (the irreducible trio is endpoint + key + deployment) to
> light it up. No STT, no voice UI yet — this cut is the backend gate only.

> **STT (B3-VOICE-STT-CONFIG-1) is the same opt-in shape.** Leave `OG118_STT_*`
> unset → `/stt/transcribe` returns `503` and the STT-wiring step is a no-op. Set
> the secret + endpoint + deployment to light up dictation. This persists in CI/CD
> what was first set live on the Container App (closing the staging drift): the
> reused Whisper deployment lives in the `insult-openai` Azure OpenAI account (same
> account as TTS). API version defaults to `2024-06-01` (Whisper GA).

### 5. Staging Static Web App (new, temporary)

Create a new Free SWA (e.g. `og118-web-staging` in `og118-rg`), copy its deploy
token into `AZURE_SWA_TOKEN_OG118_STAGING`. Its host → `OG118_ALLOWED_ORIGINS`.

---

## Ordering (the only dependency to respect)

The backend FQDN and the SWA host aren't known until their resources exist, and
each side needs the other's URL. Bring them up in this order:

1. Create the staging SWA → set `OG118_ALLOWED_ORIGINS` to its host.
2. Run **og118-backend** (workflow_dispatch) → note the Container App FQDN →
   set `OG118_API_URL` to it.
3. Run **og118-web-staging** → the bundle bakes the correct backend URL.
4. (If the SWA host changed CORS) re-run og118-backend to pick up
   `OG118_ALLOWED_ORIGINS`.

After bootstrap, normal pushes to `main` under the filtered paths redeploy
automatically.

---

## Validation after staging deploy

- `curl -sf https://<fqdn>/health` → `{"ok":true}`
- `curl -s -o /dev/null -w '%{http_code}' -X POST https://<fqdn>/chat/stream -d '{}'` → `401`
- CORS: preflight from the SWA host returns `Access-Control-Allow-Origin`; a
  foreign origin does not.
- **One real cloud turn** (API mode, amd64 image) — Bernard authorizes
  separately because it spends credits. Cloud runtime is NOT "verified" until
  that turn runs against ACA.

## Notes / risks

- Image is ~1.38 GB (Python + Node + Claude CLI). `min-replicas 1` avoids
  cold-start pulls; `max-replicas 1` because sessions are in-memory per replica.
- The arm64 image validated locally in Gate 1 is dev-only; CI builds amd64 — the
  in-container turn must be re-validated once on the amd64 ACA image.
- `AURITY` redeploys on any `main` push (its `deploy-azure.yml` has no path
  filter). Adding a path filter there is a separate, permissioned change.

## RAG store persistence (Projects corpora survive redeploys)

The Projects corpus (HDF5 at `FI_RAG_STORE_PATH=/opt/fi/data/...`, set in the
Dockerfile) is on the container's ephemeral disk by default — **every redeploy
(each merge) wipes it**, so the user would re-upload after every deploy. Fix: an
Azure Files share mounted at `/opt/fi/data`. Right-sized for the canary
(cents/mo, single-replica) vs a managed Postgres+pgvector (the post-Gate-3 scale
path: `FI_RAG_BACKEND=pgvector` + `FI_RAG_PGVECTOR_DSN`, fi-core ships it).

One-time setup (applied 2026-06-21; the `--image` deploys preserve the mount, but
re-apply if the Container App is ever recreated):

```bash
RG=og118-rg; ENV=og118-env; APP=og118-api; SA=og118ragstore
az storage account create -n "$SA" -g "$RG" -l eastus2 --sku Standard_LRS --kind StorageV2
KEY=$(az storage account keys list -n "$SA" -g "$RG" --query "[0].value" -o tsv)
az storage share create --name ragstore --account-name "$SA" --account-key "$KEY" --quota 5
az containerapp env storage set -n "$ENV" -g "$RG" --storage-name ragstore \
  --azure-file-account-name "$SA" --azure-file-account-key "$KEY" \
  --azure-file-share-name ragstore --access-mode ReadWrite
# Mount via `az containerapp update --yaml` (volumes + volumeMounts at /opt/fi/data)
# + env HDF5_USE_FILE_LOCKING=FALSE. STRIP the `configuration.secrets` section
# from the exported YAML before applying — exported secrets are redacted to null
# and a roundtrip would WIPE them (omission preserves them).
```

`HDF5_USE_FILE_LOCKING=FALSE` is required: HDF5's file lock fights SMB (Azure
Files). Safe here because the app is pinned `min=max=1 replica` (one writer).
Verified: upload → restart revision (wipes ephemeral disk) → retrieve WITHOUT
re-upload returns the stored value → corpus persisted on the volume.

Follow-up (not blocking): codify these steps in `og118-backend.yml` as idempotent
ensure-volume steps so a from-scratch ACA recreate is reproducible without manual
`az`.

## Deferred (gatekeeper LOW findings — follow-ups, not blocking)

- **Refuse-to-start in prod without a token:** `app.py` warns when
  `OG118_ACCESS_TOKEN` is unset but still serves (open). Harden later to refuse
  startup when a non-localhost origin is configured without a token.
- **Health check vs active revision:** `og118-backend.yml` curls `/health` but
  doesn't confirm the freshly-deployed revision is the active one. Add a
  `properties.latestRevisionName` / provisioning-state check so a stale healthy
  replica can't mask a failed new image.
