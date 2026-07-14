# AIRE — contexto para agentes

**A**rtificial **I**ntelligence **R**eflector **E**nvelope. Servidor HTTP que envuelve
el Claude Agent SDK y refleja el transcript de sesiones a Postgres.

---

## El espíritu (léelo antes que los hechos)

> *Aire,*
> *soñé por un momento que era*
> *aire: oxígeno, nitrógeno y argón*
> ***sin forma definida ni color.***
> *Fui aire volador.*
>
> — Mecano, «Aire» (J. M. Cano, 1984)

El acrónimo llegó después. **El nombre ya existía, y era mejor.** La canción de 1984
resultó ser la especificación del proyecto, y no por casualidad — porque describe
exactamente lo que descubrimos:

| La canción | La arquitectura |
|---|---|
| ***«sin forma definida ni color»*** | El contenedor **no guarda nada**. El agente sin cuerpo. Es el tagline. |
| ***«oxígeno, nitrógeno y argón»*** | Los tres: **la memoria** (Postgres), **la obra** (git), **el cuerpo** (el contenedor, prestado). |
| ***«iba pasando, qué curioso, al estado gaseoso»*** | El día que nació esto: se empezó con una VM —cuerpo, disco, SSH, IP— y se fue desinflando hasta que no quedó materia. |
| ***«este cuarto es muy pequeño para las cosas que sueño»*** | La pregunta original era *"¿qué diferencia hay entre EC2 y una VM de Azure?"*. El cuarto era esa pregunta. |
| ***«me volví otra vez humano. No faltéis al funeral.»*** | **En la canción, recuperar el cuerpo es la muerte.** Y aquí igual: **AIRE muere el día que su memoria vuelve a depender de un cuerpo** — de un disco que se borra a los 30 días, de una máquina que hay que mantener viva, de una base que es de otro. |

**Mientras siga siendo aire —sin forma, en la base del dueño, sin cuerpo que perder— no
hay funeral.** Esa es la prueba de fuego de cualquier decisión de diseño en este repo:

> *¿Esto le devuelve un cuerpo al agente? Entonces no.*

Por eso murieron la VM efímera, la VM eterna, Managed Agents y el disco persistente. Todas
eran cuerpos.

## La génesis — de dónde salió la forma (no se inventó aquí)

La pregunta original —*"¿qué diferencia hay entre un EC2 y una VM?"*— tenía una respuesta
que Bernard ya había visto trabajando años atrás, en una empresa de rastreo GPS: **EC-GPS**
(`ec-gps.com`, de Carlos Feria Tapia, Zapopan). Su máquina de ingresos completa, hasta hoy,
es esto:

- Los **receptores GPS empujan** su posición por **GPRS** a un servidor siempre prendido.
- Ese servidor —*"el centro de gestión"*— es un **daemon de Perl** escuchando en unos puertos,
  que vivía en una **VM de Linux en un droplet**, mantenida por **SSH**.
- El daemon **parsea** cada paquete y lo **escribe en una tabla append-only, `gps_logs`.**
- El backend **PHP** (`/app`, la consola) es **el mesero**: solo **lee** `gps_logs` y la muestra
  en un mapa. Nunca la escribe. Es reemplazable (GoDaddy, Vercel, da igual).

Ésa es la respuesta al EC2-vs-VM: para un daemon-que-escucha, **un EC2 y una VM en un droplet
son lo mismo** — un cuerpo Linux prendido 24/7 con un puerto abierto y SSH. No hace falta la
elegancia de AWS; hace falta un cuerpo que no se apague.

**AIRE es esa máquina, pieza por pieza** — no es una analogía, es el plano literal:

| EC-GPS (la máquina de Carlos FT) | AIRE |
|---|---|
| receptores GPS empujan por GPRS | apps empujan prompts por HTTP |
| daemon de **Perl** escuchando en un puerto | el **engine** dueño del SDK (`aire/engine.py`) |
| parsea y escribe `gps_logs` (append-only) | refleja el transcript al `session_store` (append-only, Postgres) |
| el **mesero PHP** lee y muestra | el **SSR** lee y te lo pinta en vivo |
| VM de Linux en droplet, SSH | el servidor always-on |

El parser de Perl convertía un paquete GPRS de formato fijo en un renglón con un regex. **El de
AIRE convierte un prompt en una sesión que razona.** Mismo esqueleto; el paso de parseo se
volvió inteligencia. Y la única evolución sobre EC-GPS: su magia está **soldada a un cuerpo
mortal** (si el droplet muere, muere `gps_logs` y muere el negocio); AIRE le **arranca el cuerpo
a la memoria** — `gps_logs` se vuelve Postgres, en la base del dueño. Por eso *"sin cuerpo que
perder"*.

## El mesero y la magia — el log es la verdad, la vista es un caché (respaldo científico)

La distinción mesero-vs-magia **no es intuición: es el teorema central de la ingeniería de datos
moderna.** Verificado en literatura canónica (algunas peer-reviewed) por `/histerical-search`:

- **Jay Kreps, «The Log»** (creador de Kafka, LinkedIn Eng): *el log es la abstracción de
  almacenamiento más simple posible —append-only, totalmente ordenado por tiempo—* y **la tabla
  es un caché / vista derivada del log.** No entiendes bases de datos, replicación, consenso ni
  control de versiones sin entenderlo.
  <https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying>
- **Pat Helland, «Immutability Changes Everything»** (ACM Queue / CIDR 2015): *"los contadores no
  usan borradores"* — todo es append-only, y **«el contenido de la base de datos es un caché de
  los últimos valores que están en los logs».** <https://queue.acm.org/detail.cfm?id=2884038>
- **WAL / ARIES** (lo implementan Postgres, Oracle, MySQL): la durabilidad se logra escribiendo
  primero a un **log append-only secuencial** — más rápido que el acceso aleatorio.
- **Martin Fowler, Event Sourcing**: el **event store append-only es la única fuente de verdad**;
  el estado es una vista derivada. Ejemplo canónico: el control de versiones (el log de commits es
  la verdad; el working copy es derivado). <https://martinfowler.com/articles/201701-event-driven.html>

**Consecuencia dura para este repo** (es `[[log-es-la-verdad]]`, la regla del repo):

- El **`session_store` (transcript append-only en Postgres) es LA VERDAD** — la magia. El **SSR /
  `render.py` es la vista derivada** — el mesero. Por eso *matar el proceso → `GET` → repinta desde
  Postgres* funciona: es event sourcing (reconstruir el estado reprocesando el log), no un truco.
- **NUNCA** dejes que la vista renderizada, el pool en RAM, ni ningún caché se vuelvan la fuente de
  verdad. El transcript append-only es la única verdad; todo lo demás se deriva de él.
- El **engine es el daemon-que-escucha** (patrón Reactor / event loop, el problema C10K de 1999).
  Lo único nuevo entre el `accept()` y el `INSERT` es que el parser ahora razona. La IA es el
  *transform*; el log y el socket son eternos y no se tocan.

---

Todo lo de abajo fue **verificado contra el código fuente del SDK instalado**
(`claude-agent-sdk` 0.2.116) o contra las docs oficiales — nunca contra memoria.
Si vas a contradecir algo de aquí, verifícalo primero de la misma forma.

## Las decisiones, ya tomadas

1. **AIRE es un SERVICIO, no una librería.** No se importa: se llama por HTTP. Así el
   SDK vive en un solo sitio, las credenciales de Postgres viven en un solo sitio, y
   cualquier lenguaje puede hablarle.
0. **EL SERVIDOR ES LA INTERFAZ — SSR, no una API JSON.** Ésta es la tesis central y lo
   que separa a AIRE de todo lo demás. Los otros exponen el SDK como API y te dejan
   construir el frontend (agent-webkit = hooks de React; el cookbook = JSON sobre SSE).
   AIRE **devuelve HTML renderizado en el servidor, que se va escribiendo solo** conforme
   el agente piensa. `GET /projects/avatar` → una página, con el agente trabajando, en
   vivo. Sin React, sin npm, sin build, sin frontend.
   - Consecuencia gratis: la "página para ver mis sesiones" **no es otro proyecto** — es
     el mismo servidor.
   - Reto técnico real: un agente no responde en un request (piensa, usa herramientas,
     corrige). Hace falta **HTML en streaming**: la página llega inmediata y los eventos
     del SDK la van pintando. No es SSR clásico de un solo disparo.
   - Por eso ninguno de los seis repos encontrados servía: todos son API-first.
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
