# AIRE — contexto para agentes

**A**rtificial **I**ntelligence **R**eflector **E**nvelope. Servidor HTTP que envuelve
el Claude Agent SDK y refleja el transcript de sesiones a Postgres.

Todo lo de abajo fue **verificado contra el código fuente del SDK instalado**
(`claude-agent-sdk` 0.2.116) o contra las docs oficiales — nunca contra memoria.
Si vas a contradecir algo de aquí, verifícalo primero de la misma forma.

## Las decisiones, ya tomadas

1. **AIRE es un SERVICIO, no una librería.** No se importa: se llama por HTTP. Así el
   SDK vive en un solo sitio, las credenciales de Postgres viven en un solo sitio, y
   cualquier lenguaje puede hablarle.
2. **Una sola base, un `project_key` por proyecto.** El `SessionKey` del SDK ya trae
   `project_key`; su docstring dice *"Multi-tenant deployments should set this."*
3. **La memoria (transcript) va a Postgres. La obra (los archivos) va a git.** Separadas
   a propósito.
4. **El contenedor no guarda nada.** `CLAUDE_CONFIG_DIR=/tmp`.

## Lo que NO hay que escribir — ya existe

- **El store de Postgres**: `examples/session_stores/postgres_session_store.py` en
  [claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python).
  Usa asyncpg, PK `(project_key, session_id, subpath, seq)`. **Cópialo, no lo escribas.**
  (Ya se cometió ese error una vez: se escribió a mano un store que ya existía.)
- **El servidor HTTP**: `claude_agent_sdk/hosting/` en
  [claude-cookbooks](https://github.com/anthropics/claude-cookbooks) — FastAPI + SSE +
  `POST /sessions/{id}/messages` + Dockerfile + K8s + Modal.
- **La suite de conformance**: `from claude_agent_sdk.testing import run_session_store_conformance`
  — 14 contratos, viene dentro del paquete. Córrela contra cualquier store.

## El contrato HTTP

Lo que el server oficial (`claude-cookbooks/hosting/server.py`) **ya expone**, verificado
leyendo su código:

```http
GET  /health
POST /sessions/{session_id}/messages
     Authorization: Bearer <AGENT_AUTH_TOKEN>    # sí tiene auth: _require_token + compare_digest
     { "prompt": "..." }
     → text/event-stream  (event: message … event: done)
```

Lo que **AIRE** expone, abriendo el eje que al cookbook le falta (tiene `cwd="/app"`
hardcodeado → un solo proyecto):

```http
POST /projects/{project}/sessions/{session}/messages
```

Mapea 1:1 al `SessionKey` del SDK: `{project_key, session_id}`. El SDK exige que
`session_id` sea **UUID** (lo valida), pero **sí deja fijarlo** → derívalo determinísticamente
del nombre con `uuid5(NS, "avatar/manuscrito")`: nombres legibles afuera, UUIDs adentro,
sin tabla de mapeo.

## Lo que SÍ hay que escribir (~150 líneas)

Es lo que el cookbook oficial **no** trae:

1. Cablear `session_store=` en las `ClaudeAgentOptions` (el cookbook no lo hace: mira
   su `_build_options()`).
2. `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` por proyecto (tiene `cwd="/app"` hardcodeado).
3. Aislamiento multi-tenant: `setting_sources=[]`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
4. Manejar el evento `mirror_error` y deduplicar por `entry.uuid` en `append()`.
5. Tirar su `_remember()` / `hosting_session_map.json` (el dict en RAM): con `session_id`
   fijable + `uuid5`, no hace falta mapeo alguno.

## Hechos verificados del SDK (no los re-descubras)

- **`session_id` SÍ se puede fijar.** `subprocess_cli.py:355` → `cmd.extend(["--session-id", ...])`.
  **No hace falta una tabla de mapeo** de id externo a id del SDK.
- **`session_store` y `enable_file_checkpointing` son INCOMPATIBLES.** El SDK lanza
  `ValueError` (`session_store_validation.py`): *"checkpoints are local-disk only and
  would diverge from the mirrored transcript."* → **El scratch/permanente se resuelve
  con git (ramas, `git mv`), no con `rewind_files()`.**
- **`session_store` es un espejo, no un reemplazo.** El subproceso sigue escribiendo el
  JSONL a disco; el adapter recibe **una copia secundaria**. Al resumir, el SDK carga
  del store y lo materializa en un temp dir con `CLAUDE_CONFIG_DIR`.
- **`session_store_flush='eager'`** escribe cada entrada al momento → sin ventana de
  pérdida si el contenedor muere. `'batched'` es más rápido pero puede perder.
- **`continue_conversation` + `session_store` exige `list_sessions()`** implementado.
- **Solo `append()` y `load()` son obligatorios** en el Protocol; los otros cuatro son
  opcionales y el SDK los prueba en runtime.
- **Hay dos memorias distintas**: `SessionStore` (transcript crudo) y la
  **Memory Tool** (`memory_20250818`, hechos destilados, client-side → tu misma base).
- **`SandboxSettings`** confina al agente (bash sandbox, `excludedCommands: ["git"]`).
  El "contenedor que no se automodifica" es **config, no infra**.
- **Hook `Stop`** → ahí va el `git commit && push` al cerrar cada job.
- **`max_budget_usd`** → tope duro de gasto por query.

## Rutas descartadas (no las re-propongas)

- **VM efímera con SSH** (el `air-lite` original): es el Agent SDK reinventado con
  `boto3` + `paramiko`. Muerto.
- **VM persistente ("never terminate")**: reinventa git como almacenamiento y paga renta
  24/7 por un disco que es punto único de falla. Muerto.
- **Managed Agents** (el hosted de Anthropic): la memoria vive **de su lado**, sin
  `session_store`, no elegible para ZDR, y cobra **$0.08/hora de sesión** además de
  tokens. Mata el dashboard y las queries propias. Muerto para este caso.
- **Adoptar Agno AgentOS**: su `ClaudeAgent` **no pasa `session_store`** (0 ocurrencias
  en su código) y guarda el mapeo en un `Dict` en RAM → pierde el `resume` al reiniciar.
  Verificado leyendo `libs/agno/agno/agents/claude/agent.py`. Tiene el mismo agujero
  que AIRE viene a tapar.
- **Adoptar ArcReel**: es **AGPL-3.0** (viral) y su `DbSessionStore` es una librería
  interna de su producto, no un servicio. No se puede llamar desde otros proyectos.

## El estado del arte (verificado leyendo código, julio 2026)

**No es cierto que "nadie cablee el `session_store`"** — esa afirmación estuvo en este
archivo y era **falsa**. La verdad, por ejes:

| | Refleja a una DB | Servidor HTTP reutilizable | Housekeeping |
|---|---|---|---|
| `claude-cookbooks/hosting` (oficial) | ❌ dict en RAM + disco | ⚠️ un proyecto (`cwd="/app"`) | ❌ |
| Agno (41k ⭐) | ❌ dict en RAM + disco | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ `DbSessionStore`, SQLAlchemy (PG/SQLite) | ❌ lib interna | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

ArcReel es la prueba de que el caso de uso es real: su producto es novela → personajes →
escenas → video, y llegaron a la misma solución. Pero **ninguno de los tres barre**: cero
`ttl`/`retention`/`cleanup`/`archive` en su código.

## El housekeeping es un pilar, no un extra

El docstring del `SessionStore` **delega la retención al adapter, por escrito**:

> *"The SDK **never deletes** from your store… Retention is the adapter's responsibility —
> implement TTL, object-storage lifecycle policies, or scheduled cleanup according to your
> compliance requirements (e.g. ZDR/HIPAA retention windows)."*

Es decir: la memoria **acumula para siempre** por diseño, y limpiarla es trabajo del
adapter. Nadie lo ha hecho. Ése es el hueco más limpio de AIRE.

## Cómo trabajar aquí

- **Verifica contra el código, no contra la doc ni contra tu memoria.** Esta sesión
  produjo tres afirmaciones falsas que solo el código fuente desmintió.
- **Bernard distingue aprender de construir.** Cuando está entendiendo algo, no te
  adelantes a escribir código: se lo robas. Pregunta si no es obvio cuál de los dos modos
  es el activo.
