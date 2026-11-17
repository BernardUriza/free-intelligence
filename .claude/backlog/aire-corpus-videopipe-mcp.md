# AIRE como almacén del corpus de videopipe + MCP de proyectos/persona

Status: **In progress** — construido y probado en un box de desarrollo el 2026-11-16, PR abierto, SIN desplegar
Propuesta: 2026-11-16 por Bernard (*"explora muy bien Free Intelligence para que entiendas aire y cómo se va a
guardar cada dato … si necesitas mejorar el MCP, hazlo. Sobre todo el de persona … que también haya otro para
manejar archivos, proyectos y también chats"*). Tarjeta técnica del lado AIRE (en inglés, por su ley):
[`apps/aire-server/.claude/backlog/55-…`](../../apps/aire-server/.claude/backlog/55-a-project-reads-its-own-corpus-and-chats.md).

## Mapa del sistema (verificado contra el código, 2026-11-16)

- **AIRE** (`apps/aire-server/server`) es un daemon FastAPI en el droplet de DigitalOcean detrás de
  `gate.bernarduriza.com`. Es la puerta de turnos, la de gateway `/v1/*` y la de OpenAI `/openai/v1/*`.
- **Un proyecto de AIRE es una casita**: el directorio `/opt/aire/workspaces/<p>/` en el disco del droplet, que
  es mortal. Su persona es el `CLAUDE.md` (Codex lo lee como `AGENTS.md`). La persona se espeja append-only en
  la tabla `aire_casita` de Postgres y `restore` la rematerializa.
- **Los chats** viven en el Postgres de AIRE (Azure, con PITR de 7 días). El transcript de Claude está en
  `claude_session_store` y el de Codex o ACP en `aire_agent_log`. Una sesión es `uuid5(nombre)`, sin tabla de
  mapeo, y el mismo nombre reanuda.
- **Los documentos** viven en `aire_corpus_chunk` del mismo Postgres, con FTS `spanish` y acentos plegados
  (#46/#47). El `owner` sale del `@base` de la casita. **AIRE no usa HDF5.** El HDF5 está en fi-core
  (`stores-hdf5`, `HDF5ChunkStore`) y lo usó el Proyectos de og118 en Azure Files, que hoy está apagado tras
  `OG118_PROYECTOS`. AIRE eligió Postgres en #46 porque el droplet tiene 512 MB y es mortal.
- **Los artefactos** son archivos que el agente escribe en la casita. Viven en disco y no se espejan: se bajan
  con `GET /projects/{p}/artifacts/…`.
- **Las tools por turno** salen de un registro cerrado, `memory`, `persona`, `rag_store` y `task_tracker`, más
  `remote_tools` (#48) por HTTPS con allowlist. Codex las monta por stdio (#54).
- **El Proyectos de og118** (registro JSON y conversaciones JSON en Azure Files) es otro sistema. Está apagado.
- **`persona_mcp` de server-bot** habla con el persona-runner de Azure Container Apps (Frugívoro, Insult) como
  Bernard. **No es el camino de Astra.** Astra es la casita `videopipe` en AIRE con `provider: codex` y
  `model: gpt-6-astra`.
- **El MCP del fi-core** de "persona" es detección de drift (`check_drift` y similares), no hablar con una
  persona. Su `rag_store` es la versión local con HDF5 o pgvector.
- **Respaldo y versiones:** Postgres tiene PITR de 7 días de Azure. Hasta hoy un documento del corpus se
  REEMPLAZABA sin historia. Con esta tarjeta cada versión queda en `aire_corpus_version`.

## Cómo se guarda cada dato del corpus de videopipe

Proyecto AIRE `videopipe` (la casita que ya usa Astra). Corpus `research`. El doc id es la ruta relativa al repo.

| Artefacto de videopipe | Entidad en AIRE | Store | Búsqueda | Historia y auditoría | Latencia para un hook PreToolUse |
|---|---|---|---|---|---|
| `corpus/casos/<tema>/sources-<id>.md` | documento | `aire_corpus_version` (texto exacto) + `aire_corpus_chunk` (índice) | FTS `spanish` por palabras; `read_document` exacto | una fila por versión con sha256, tombstone al borrar, PITR de 7 días | 0 ms con la copia local (`sync pull`); ~0.4–0.6 s por llamada al gate (medido a `/health`) |
| `corpus/backlog.md`, `corpus/lore.md`, `mapa-de-medios.md` | documento | ídem | ídem | ídem | ídem |
| `corpus/fichas/`, `corpus/series/`, `leads.md`, `clips.md` | documento | ídem | ídem | ídem | ídem |
| `editorial/` (comedy-brief, prompts, drafts) | documento | ídem | ídem | ídem | ídem |
| `editorial/prompts/astra-guionista.md` | persona de la casita | `CLAUDE.md` en disco + `aire_casita` | — | append-only en `aire_casita` | — |
| Rondas con Astra | chat | `aire_agent_log` (Codex) | `recall` en el turno; `read_chat` fuera | append-only, sin barrido | — |
| `corpus/casos/*/evidencia-*.png`, PDFs | **hueco** | no hay store durable de binarios | — | — | — |
| Filas Verified/Fragile/Never, Inserts, Síntesis | **hueco**: siguen en markdown | dentro del documento | parser del lado lector (el hook ya lo hace) | la versión del documento | igual que el documento |
| Ítems del backlog con status | **hueco**: markdown | dentro de `backlog.md` | FTS | versión del documento | — |
| Archivos por video que nombran a privados (`shots`, `cards`, `credits`, `description`) | documento | ídem, con su ruta | FTS | ídem | ídem |

**El diseño para los hooks:** el árbol sigue en la Mac en las mismas rutas, gitignorado, como copia de trabajo.
AIRE guarda la copia durable con versiones. `sync.py push` sube solo lo que cambió (por sha) y `pull` restaura.
Así `insertos-antes-de-la-toma.py` y `idea-se-anota-ya.py` siguen leyendo `corpus/` y `editorial/` sin red y
sin cambio. Solo hace falta un paso de sincronización: un hook Stop o PostToolUse que haga `push` de lo escrito.

## Lo que se construyó

Lado daemon (`apps/aire-server/server/aire`):
- `corpus_versions.py`: cada versión con su texto exacto. Una idéntica no se agrega y un borrado es tombstone.
- `document_door.py`: corpora, texto exacto por versión e historia. Acepta doc ids con `/`.
- `transcripts.py` y `chat_door.py`: proyectos, sesiones de un proyecto y turnos de una sesión, de las dos tablas.
- `intake.owners_only`: las lecturas nuevas son solo para tokens constantes. Una llave invitada recibe 403.
- `codex_mcp.CODEX_TOOLS` suma `rag_store`, para que Astra busque en su expediente a media vuelta.

Lado cliente (`apps/aire-server/mcp`, stdlib, no viaja al droplet):
- `projects_mcp.py`, servidor `aire-projects` con 11 tools: `list_projects`, `list_corpora`, `read_persona`,
  `list_documents`, `read_document`, `write_document`, `search_documents`, `document_history`,
  `delete_document`, `list_chats` y `read_chat`.
- `persona_mcp.py`, servidor `aire-persona` con 4 tools: `ask_persona` (la misma `session` reanuda; con
  `tools: [rag_store, memory]` la persona lee sola los documentos y chats de su proyecto), `session_exists`,
  `read_persona` y `set_persona`.
- `sync.py`: `push` y `pull` de un árbol. Los binarios se saltan y se listan.

Pruebas: 476 verdes en `apps/aire-server/server` (eran 451). `test_mcp_clients.py` corre las tools MCP contra
la app real, el Postgres local y un turno Codex con modelo falso que busca en su expediente, reanuda la sesión
y luego se lee como chat. Es la prueba de las dos puntas del camino, cada una por la vía del producto.

## Registro en videopipe (`.mcp.json`, sin secretos; el token se lee de su archivo en cada llamada)

```json
{
  "mcpServers": {
    "aire-projects": {
      "type": "stdio", "command": "python3",
      "args": ["-I", "${HOME}/Documents/free-intelligence/apps/aire-server/mcp/projects_mcp.py"],
      "env": {"AIRE_PROJECT": "videopipe", "AIRE_CORPUS": "research"}
    },
    "aire-persona": {
      "type": "stdio", "command": "python3",
      "args": ["-I", "${HOME}/Documents/free-intelligence/apps/aire-server/mcp/persona_mcp.py"],
      "env": {"AIRE_PROJECT": "videopipe", "AIRE_CORPUS": "research",
              "AIRE_PERSONA_PROVIDER": "codex", "AIRE_PERSONA_MODEL": "gpt-6-astra",
              "AIRE_PERSONA_TOOLS": "rag_store,memory"}
    }
  }
}
```

## Para producción (una sola decisión de Bernard)

1. Mergear el PR. `aire-server-deploy-server.yml` despliega al droplet, y en el arranque se crea
   `aire_corpus_version` con el rol `aire`, así que el lector lo ve. No hay variables nuevas.
2. Agregar el `.mcp.json` de arriba en videopipe y reiniciar Claude Code.
3. `sync.py push corpus --prefix corpus/` y `push editorial --prefix editorial/`, con `--project videopipe`
   y `--corpus research`.
4. Un turno real de Astra con `tools: ["rag_store"]` que cite un dato del expediente. Ese es el recibo.
5. Después, gitignorar `corpus/` y `editorial/` en el repo público y dejar el hook de `push`.

## Decisiones abiertas de Bernard

1. **Leer chats en el daemon.** La lectura amplía [[write-only-daemon]]. Pasa su criterio, porque el que llama es
   dueño de las filas y las usa un agente, pero es la más cercana al trabajo del front. ¿Se queda en el daemon o
   se va al front con `aire_reader`?
2. **Binarios** (PNG de folios, PDFs). Hay tres opciones: disco del droplet (mortal, 512 MB), `bytea` en
   Postgres (vigilado por `growth.py`, techo de 250 MB) o Azure Blob.
3. **Filas estructuradas** (Verified/Fragile/Never, Inserts, backlog con status). Pueden seguir en markdown con
   parser en el lector, como hoy, o pasar a una tabla tipada (JSONB) con su propia puerta.
4. **Borrado real.** Hoy un borrado deja la historia. Para un nombre privado que debe desaparecer hace falta un
   verbo `purge`.
5. **Un corpus o varios** (`research`, o `corpus` y `editorial` por separado). Y si la persona de Astra pasa de
   `editorial/prompts/astra-guionista.md` a la casita con `set_persona`.
