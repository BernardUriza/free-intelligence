#!/usr/bin/env bash
# Arranca el servidor de Fénix en local.
#
# Existe porque la configuración vivía sólo dentro del proceso en ejecución:
# reiniciarlo obligaba a reconstruir diez variables de memoria, y una omitida
# —el token del mostrador, por ejemplo— abre la app entera sin avisar.
#
# El intérprete es el de og118 (`apps/og118/server/.venv`): Fénix no tiene venv
# propio porque no tiene dependencias propias, monta su router sobre la app de
# og118. El `--app-dir` es lo que hace que `fenix_app` gane el import sobre el
# `app.py` de og118.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DATOS="${FENIX_DATA_DIR:-$HOME/.fenix-data}"
mkdir -p "$DATOS"

# El token del mostrador es un secreto y no se versiona. Sin él la app corre en
# modo abierto (útil en local, inaceptable desplegada), y el arranque lo dice.
if [[ -z "${FENIX_ADMIN_TOKEN:-}" && -f "$HOME/.secrets/fenix.txt" ]]; then
  FENIX_ADMIN_TOKEN="$(grep '^FENIX_ADMIN_TOKEN=' "$HOME/.secrets/fenix.txt" | cut -d= -f2-)"
  export FENIX_ADMIN_TOKEN
fi
# Sin token el servidor se niega a arrancar (rbac.exigir_config). Este script es
# para local, así que declara el modo abierto a propósito — un deploy que no lo
# haga falla ruidosamente, que es justo lo que se quiere.
if [[ -z "${FENIX_ADMIN_TOKEN:-}" ]]; then
  echo "AVISO: sin FENIX_ADMIN_TOKEN — modo abierto local, todos son mostrador." >&2
  export FENIX_MODO_ABIERTO=1
fi

# La credencial del modelo. Con llave de API se puede atender a terceros; con el
# token de suscripción NO (uso personal, ToS de Anthropic) — `arranque.py` lo
# exige y aborta si encuentra las dos, porque el SDK elige por entorno y ahí no
# se puede afirmar cuál paga.
if [[ -z "${ANTHROPIC_API_KEY:-}" && -f "$HOME/.secrets/fenix-anthropic-api-key.txt" ]]; then
  ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' "$HOME/.secrets/fenix-anthropic-api-key.txt" | cut -d= -f2-)"
  export ANTHROPIC_API_KEY
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  # Este script suele lanzarse desde una sesión que YA trae el token OAuth en el
  # entorno (Claude Code lo exporta). Heredarlo aquí dispararía el aborto por
  # ambigüedad, así que se quita explícitamente: con llave, manda la llave.
  unset CLAUDE_CODE_OAUTH_TOKEN
else
  # Sin llave, el único usuario es Bernard en su máquina y la suscripción es
  # legítima. Se declara a propósito, no por omisión.
  export FENIX_USO_PERSONAL=1
fi

export FI_PERSONA_PATH="$REPO/apps/fenix/server/prompts/persona.md"
export FI_EXTRA_MCP="fenix-expedientes:$REPO/apps/fenix/server/fenix_mcp.py"
export FENIX_EXPEDIENTES_PATH="$DATOS/expedientes.json"
export FENIX_ADMIN_EMAILS="${FENIX_ADMIN_EMAILS:-lidia@fenix.mx,ximena@fenix.mx}"

# Datos de la papelería, separados de los de og118: comparten runtime, no archivos.
export OG118_AUTH_MODE=bearer
export OG118_PROJECT_REGISTRY_PATH="$DATOS/projects.json"
export OG118_CONVERSATIONS_PATH="$DATOS/conversations"
export OG118_ALLOWED_ORIGINS="http://localhost:3100,http://127.0.0.1:3100"
export FI_RAG_STORE_PATH="$DATOS/fi_rag_store.h5"

cd "$REPO/apps/og118/server"
exec ./.venv/bin/uvicorn --app-dir "$REPO/apps/fenix/server" fenix_app:app \
  --port "${FENIX_PORT:-8119}" "$@"
