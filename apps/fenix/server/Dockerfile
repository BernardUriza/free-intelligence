# Fénix — el runtime de og118 con el router de la papelería montado encima.
#
# Se construye desde la RAÍZ del repo, porque copia tres cosas de distintos
# lugares del monorepo:
#   docker build -f apps/fenix/server/Dockerfile -t fenix-server:prod .
#
# Casi todo es idéntico al Dockerfile de og118 a propósito: Fénix NO es un
# servidor nuevo, es su app más un router. Lo que cambia son tres líneas al
# final —copiar el código de Fénix, sus dependencias, y arrancar `fenix_app` en
# vez de `app`— y ése es justamente el punto del experimento.

FROM python:3.12-slim-bookworm

# Node 20 + el CLI de Claude en la versión que espera claude-agent-sdk.
# fi-runner maneja el modelo a través de ese CLI (no hay backend Python puro),
# así que el CLI viaja en la imagen aunque la credencial se inyecte en runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code@2.1.162 \
 && apt-get purge -y curl gnupg && apt-get autoremove -y \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY apps/packages/fi-core   /opt/fi/packages/fi-core
COPY apps/packages/fi-runner /opt/fi/packages/fi-runner
RUN pip install --no-cache-dir \
      "/opt/fi/packages/fi-core[mcp,stores-hdf5]" \
      "/opt/fi/packages/fi-runner[claude,auth,postgres]"

# El runtime de og118: Fénix lo importa tal cual.
COPY apps/og118/server /opt/fi/server
RUN pip install --no-cache-dir -r /opt/fi/server/requirements.txt

# Lo propio de la papelería.
COPY apps/fenix/server /opt/fi/fenix
RUN pip install --no-cache-dir -r /opt/fi/fenix/requirements.txt

RUN useradd --create-home --uid 10001 fenix

# Los datos del negocio —expedientes, conversaciones, el corpus de la lista
# maestra— van aquí. En Azure este directorio es un volumen de Azure Files: sin
# él, cada reinicio del contenedor borra las cotizaciones de los clientes.
RUN mkdir -p /opt/fi/data && chown fenix:fenix /opt/fi/data
# Dónde vive el runtime de og118 DENTRO de la imagen. El layout del monorepo
# (`apps/fenix/server` junto a `apps/og118/server`) no sobrevive aquí, así que
# el cálculo relativo de fenix_app.py apuntaría a un directorio inexistente.
ENV FI_OG118_DIR=/opt/fi/server \
    FI_RAG_STORE_PATH=/opt/fi/data/fi_rag_store.h5 \
    FENIX_EXPEDIENTES_PATH=/opt/fi/data/expedientes.json \
    OG118_CONVERSATIONS_PATH=/opt/fi/data/conversations \
    OG118_PROJECT_REGISTRY_PATH=/opt/fi/data/projects.json \
    FI_PERSONA_PATH=/opt/fi/fenix/prompts/persona.md \
    FI_EXTRA_MCP=fenix-expedientes:/opt/fi/fenix/fenix_mcp.py

USER fenix
ENV HOME=/home/fenix

# El WORKDIR es el de og118 y `--app-dir` mete el de Fénix ANTES en el path.
# Ese orden es lo que hace que `fenix_app` gane el import sobre `app.py`; al
# revés, Fénix se importaría a sí mismo y reventaría en círculo.
WORKDIR /opt/fi/server
EXPOSE 8118

# Sin ANTHROPIC_API_KEY el arranque FALLA a propósito (arranque.py): servir a
# la papelería o al cibercafé con un token de suscripción rompe el ToS de
# Anthropic, y un contenedor mal configurado se ve igual que uno sano.
CMD ["uvicorn", "--app-dir", "/opt/fi/fenix", "fenix_app:app", "--host", "0.0.0.0", "--port", "8118", "--log-level", "info"]
