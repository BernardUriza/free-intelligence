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
if [[ -z "${FENIX_ADMIN_TOKEN:-}" ]]; then
  echo "AVISO: sin FENIX_ADMIN_TOKEN — todos los visitantes son mostrador." >&2
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
