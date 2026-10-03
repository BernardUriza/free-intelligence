# Backlog — server-bot (repo renombrado de `discord-bot` el 2026-09-23)

> **Rename 2026-09-28:** el paquete `khimeras_shared/` ahora se llama `persona_core/`.
> Los items de este folder son bitácoras fechadas y conservan el nombre viejo: lee
> `khimeras_shared/x` como `persona_core/x` en el árbol vivo.

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook. Items Done se retiran del folder (limpiezas
2026-07-05 y 2026-08-06); su historia vive en git.

**Última auditoría contra el repo y prod: 2026-09-23** (`git log --since=2026-09-09`,
`grep -rn`, `az containerapp show` de las tres apps —grace period, `minReplicas`,
revisión, imagen—, `az acr list`, `gh issue view`, `gh pr list`, `curl -I` al blob
del dashboard). Las anteriores: 2026-09-09, 2026-09-07 y 2026-08-06. **Alcance
honesto de hoy:** se re-verificaron las filas que el trabajo del 09-10 → 09-23
pudo mover (drenaje, frío del runner, Valentis, CD fake-green, CVE, dashboard,
rename, cadenas cortadas, proactividad); **no se re-verificaron** el builder de
turno, Frugívoro, Fruggy, el ML-stack ni el servidor llave en mano — sus filas
siguen con la fecha de su último recibo. Sin `psql` hoy.

**Lo que cambió desde el 09-09:**
- **Un item se retira: el drenaje graceful.** Su archivo ya decía *Done
  (2026-09-22)* mientras esta tabla lo tenía *In progress* — la misma
  contradicción que el 09-09 corrigió en AIRE etapa 1 y en Frugívoro. Y el
  09-23 lo superó: el turno viaja por boleto durable en las dos costuras
  (v4.40.0–4.40.4) y sobrevive un restart a media generación sin segunda
  respuesta. Recibos abajo, en *Retirados*.
- **Dos items nuevos del 09-23** (frío del runner, fase B de reattach) entran
  ya con su fila.
- **El item del CD fake-green** (09-18) estaba colgado al final de un bloque
  de *Retirados* del 07-05 sin ser retirado ni Done: sube a la tabla.

**Los dos huecos que el 09-07 declaró, cerrados hoy:**
- *Postgres (sin acceso)* → **sí hubo acceso** (credencial de `~/.secrets/`,
  consumida a variable, nunca impresa; sólo `SELECT`/`COUNT`). Cerró la deuda más
  vieja del folder: la ingesta del corpus de Frugívoro, sin verificar desde el
  2026-08-06.
- *`khimeras_shared/corpus/` (otro agente lo estaba podando)* → ese agente era
  `6ba7a61` (v4.38.6, issue #62), del mismo 09-07: borró 1,017 líneas de corpus.
  Dejó **tres items rancios** que el 09-07 no pudo recoger porque el borrado
  ocurría mientras se auditaba.

**Y dos contradicciones internas del 09-07, corregidas aquí** — las dos son la
misma forma: el commit de esa auditoría ARREGLÓ algo y su propio índice lo dejó
escrito como pendiente. Ver las filas de AIRE etapa 1 y de Frugívoro.

**No verificado hoy:** que Valentis conteste en vivo en #general (misma deuda que
el 09-07), y la re-auditoría de alcanzabilidad CVE por CVE — se verificó la lista
de `--ignore-vuln` y los pisos de versión, no el análisis de cada CVE.

| Item | Status | Hook |
|---|---|---|
| [Servidor llave en mano con personas de Alex](servidor-llave-en-mano-personas-alex.md) | 🔒 **Congelado hasta 2027** (candado de Bernard 2026-08-17, `84cfe15`) | re-confirmado 2026-09-09: el ÚNICO commit al item desde el candado es `1af6718`, la auditoría del 09-07, y su diff son 4 líneas de status. Cero ejecución ante terceros. Nada que proponer aquí |
| [Valentis — quien se queda](persona-acompanamiento-issues-alex.md) | **Fase 1 SHIPPED** (2026-08-25, v4.32.75–80) — **fase 2: 2 de 4 piezas con issue** (corpus DONE, overlay propio OPEN) | re-verificado 2026-09-23: **#61 CLOSED 09-19** — el corpus de Valentis existe (`c22b965` v4.38.37 estrena el eje ético de las cinco personas; `867f821` v4.38.40 suma el criterio clínico de Guerrero), así que la pieza "corpus" de la fase 2 está hecha. **#84 OPEN (Alex)** — *Valentis no tiene su capa de tono para usuario vulnerable* — es el `preset_vulnerable_overlay.md` propio, la pieza que las notas de este item marcaron como hallazgo #1 desde el 08-12. Quedan sin issue: facetas por tema y presets propios. **MERGED 09-23** (6e4315f) — **PR #82 de Alex** (*"quien se queda"* sustituye a *"acompañamiento psicológico"* en registry, backlog y test). `#80` ya cerrado vía #81 (09-18). **No verificado:** que Valentis conteste en vivo (deuda desde el 09-07) |
| [Dashboard: data plane fósil](dashboard-data-plane-fossil.md) | **In progress** — fake-green eliminado 2026-08-06 (`34bf41c`, v2.4.0); fork de Bernard sigue abierto | re-verificado 2026-09-23, sin cambios: `curl -I .../insult-bot/metrics.json` → `200`, `Last-Modified: Thu, 25 Jun 2026` — **90 días de fósil**. `git log --since=2026-09-09 -- dashboard/` → vacío. Fork: recablear el emisor en `persona_gateway` o congelar |
| [La proactividad murió en la purga](proactividad-muerta-restaurar-en-el-host.md) | Accepted · **slice 1 HECHO** 2026-08-06 (`aae8e2c`, v4.32.33); slices 2–5 sin arrancar | re-verificado 2026-09-23 (el único importador de `khimeras_shared.proactive` sigue siendo `tests/core/test_proactive.py`; cero `ProactiveWorker` fuera de tests); el 09-09 ya lo había dejado igual, las cuatro afirmaciones intactas: `khimeras_shared/proactive.py` y su test viven, el ÚNICO import es el propio test, cero `ProactiveWorker` en `demux_ai/`, y `store_world_scan` sólo lo llama `tests/core/test_world_scans.py` — cero escritores en producción. **Cuidado con el falso positivo:** `khimeras_shared/proactive_agenda.py` SÍ tiene consumidor vivo (`persona_gateway/workers/agenda.py:11`), pero ése es el worker reactivo de `[AGENDA:]`, no este núcleo. **No verificado:** el contenido de la tabla `world_scans` en Postgres |
| [Builder de turno unificado](turn-builder-unificado.md) | **Absorbido en F3 del checklist (2026-09-27)** — Discord apagado, og118 es el primer cliente; lo que queda del item es extraer la tubería del turno a `run_turn(InboundTurn)`, no unificar dos puertas del gateway. Antes: 4 de 5 defectos cerrados 2026-09-09 (v4.38.26) | re-verificado 2026-09-09: `TurnSpec`/`TurnBuilder` siguen sin existir (el único hit es un docstring de `aire_route.py:659`, que además nombra otro concepto) y `_handle`/`respond_to_invite` siguen siendo dos entry points. Pero el CI ya impone paridad, así que el refactor rinde poco; **lo que rendía eran los 5 `xfail(strict)` del arnés, y hoy quedan 2** (de 48 passed/5 xfailed a **52 passed/2 xfailed**). Cerradas: el `memory.store` y `attachment_blocks` desnudos de `_handle` (los dos que perdían la respuesta delante del humano), el `corpus_query` que iba keyed por el resumen del router, y la mitad del cuarto que escribía facts bajo el id del propio bot. Las cuatro verificadas en rojo revirtiendo cada fix. **De paso destapó una contradicción entre dos arneses del repo:** `test_gateway_corpus_wiring.py` fijaba el defecto del corpus como correcto mientras el de paridad lo marcaba xfail. Lo que queda son las dos que no son trabajo sino decisión — qué `user_id` recibe el runner cuando no hay humano, y si el host va a escuchar ediciones. Detalle: (1) ✅ el `memory.store` de `_handle` ya va guardado — un parpadeo de Postgres degrada en vez de matar el turno; (2) ✅ igual con `attachment_blocks` — un adjunto corrupto ya no se come la respuesta; (3) ✅ `corpus_query=subject_ask or reason`; (4) 🟡 media — los facts bajo el id del bot ya se descartan, pero el runner sigue recibiendo ese id como sujeto del turno; (5) 🔴 el summon-por-edición sigue muerto desde el cutover, y es capacidad nueva en el host, no un fix |
| [Frugívoro persona](frugivoro-persona.md) | **Los 4 pasos verificados** por primera vez (2026-09-09) — falta sólo el benchmark | la deuda más vieja del folder, cerrada: `psql` de sólo lectura contra prod da **858 chunks** bajo `user_id='__corpus_vegan__'` (la columna es `user_id`, no `namespace`), en 3 `source_ref` — Williams *Ethics of Diet* 749, y dos revisiones PMC de 60 y 49 — ingeridos el 2026-07-16, exactamente las 3 fuentes del MANIFEST. **Contradicción del 09-07 corregida aquí:** ese índice decía "sin acceso a Postgres" y sí lo había. **Y el item quedó rancio el mismo día:** cita `khimeras_shared/corpus/vegan_gastronomy.md` como vivo dos veces y `6ba7a61` lo borró (recuperable en `git show 798ba77:khimeras_shared/corpus/vegan_gastronomy.md`). Benchmark §1–§3 sin arrancar, sin issue |
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | **Repo RENOMBRADO 2026-09-23** (`gh repo rename`, go de Bernard; redirects de git y API verificados; Alex avisada en #general) — queda el RG, que es reconstrucción, y el barrido gradual de menciones (batch 1 el mismo día: repo/sistema y punteros rotos a la app retirada; GATED: env conda, secretos, `constitution.toml repo_id`) | re-verificado 2026-09-23 antes del rename, sin cambios en Azure: `az acr list -g insult-rg` → sólo `insultacr`; `az containerapp list` → las mismas siete apps, `discord-bot` retirada sigue `Running` con min=0, y las tres del repo corren `d02ae1d` desde GHCR (`persona-runner--0000245`, `persona-gateway--0000231`, `khimeras-host--0000163`). RG→`server-rg` sigue agendado |
| [Renombrar Frugi → Fruggy](rename-frugi-to-fruggy.md) | **Slice 1 DONE** (alias `fruggy`, `40a4fea` v4.32.45; #36 cerrado 2026-08-14) — resto en decisión de Bernard | re-verificado 2026-09-09. Registry intacto: `aliases=["frugivoro","frugi","frugívoro","fruggy"]`, `display_name="Frugívoro"`. **Ojo con el conteo: bajó de 146 a 125 hits y NO es progreso** — `6ba7a61` borró `vegan_gastronomy.md`, que traía 21 de esos hits (146 − 21 = 125, cuadra exacto). Siguen fuera el `display_name`, el username del bot en Discord y el `persona_id`/DNA/`token_env` |
| [CVE exploitability review](cve-exploitability-review.md) | **Ejecutado salvo el lote ML** (2026-09-25, v4.40.26): `--ignore-vuln` **34 → 22** | recibo 2026-09-25: env fresco desde `environment.yml` + `pip-audit` SIN ignores → en main sólo flask, starlette y torch tenían vulns; los 6 ignores de aiohttp/cryptography/msgpack/idna/pydantic-settings eran ruido muerto (el solve ya caía arreglado). Cambios: pisos explícitos para esos 5, `starlette<1.0` → `>=1.3.1` (fastapi-core 0.141 ya no capa; resuelve 1.6.0), y **fuera `azure-storage-blob`** (0 imports) — era su `azure-core` quien arrastraba `flask 2.2.5`, no pip-audit como decía el CI. Env nuevo: pip-audit con los 22 ignores → REAL none; pytest 1886 passed. Los 22 restantes son TODOS el lote ML, dueño [`ml-stack-cve-audit.md`](ml-stack-cve-audit.md) (dato para él: en el solve fresco sólo disparan PYSEC-2026-139 y PYSEC-2025-194/CVE-2025-3000). **Trampa local:** `pip.conf user=true` + `PYTHONNOUSERSITE=1` → pip-audit audita 0 deps y dice verde; usar `PIP_CONFIG_FILE=/dev/null`. **No verificado:** el solve linux-64 más allá del CI de este PR; ingress del runner no re-chequeado |
| [Arranque en frío del runner: `min=0` cuesta latencia, ya no el mensaje](runner-cold-start-min-replicas.md) | **Proposed** 2026-09-23 — decisión de Bernard: `min=1` (gasto, ~USD 100+/mes) y/o startup probe (gratis, recorta ~80 s) | `az` 2026-09-23: `persona-runner` sigue `minReplicas=0`, grace **600** (aplicado hoy, v4.40.2). Recibo del hallazgo: probe de v4.39.5 en #general 13:32 UTC → `host_turn_gave_up` a los 135 s, alta aceptada a los 169 s, dos turnos huérfanos; 7 días previos: 105 arranques, 5 give-ups. Desde v4.39.6 + v4.40.x el frío ya no mata el mensaje (alta idempotente por `job_id`, read timeout del alta 200 s, boleto durable). **Medición pendiente, no hecha:** `host_turn_gave_up` por semana después del 09-23 — si cae a cero, `min=1` compra sólo latencia |
| [Imágenes por referencia: Discord → AIRE](imagenes-claim-check-discord-aire.md) | **Done** 2026-09-25 (idea de Bernard) — cross-repo aire-server + fi-runner 0.22.0/0.23.0 + este repo (v4.41.0–v4.42.1); imágenes y documentos probados en vivo | Claim Check con Discord como almacén: el pipeline carga la URL firmada, AIRE baja los bytes. Probe en #general 22:37 UTC: Vultur describió `probe-50.png` ("MANGO 5082") en `ᵛ⁴·⁴¹·¹`. Cerrados: clase del #92, ≥5 fotos, `job_id` en logs. **Pendiente:** PDFs por referencia y borrar el camino base64 |
| [Fase B — reanudar por reattach a AIRE, no re-preguntando](aire-background-turn-reattach.md) | **Proposed** 2026-09-23 — cross-repo (aire-server + fi-runner); la fase A (v4.40.x, en prod) reanuda re-preguntando con `resumed` | AIRE ya tiene `background:true` + `GET …/status` (messages.py:50-90) pero sin idempotency key; fi-runner 0.21.7 no lo manda. Recibo para arrancar: un `aire_route_turn_resumed` que hoy duplica el mensaje del usuario en el transcript. Sin cambios desde que se escribió (mismo día) |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | **CVE tax 23 → 2 ignores** (2026-09-25, v4.40.27) — abierto: torch en host/runner (peso de imagen) + fork del dueño (Azure embeddings) | consumidor VIVO sólo en el gateway (`turn_context.py:150` → `search_facts_semantic` → `vectors.py:53`); runner y host no importan `khimeras_shared.memory`, pero las tres imágenes heredan torch de `khimeras-base`. 20 de los 23 ignores eran muertos (OSV `last_affected` ≤ lo resuelto: torch ≤2.7.1, transformers ≤5.0.0-rc0, joblib ≤1.4.2, pyjwt ≤2.10.1) → borrados + pisos en `environment.yml`. Quedan PYSEC-2026-139 y CVE-2025-3000: el fix (pytorch ≥2.11) existe pero todo build conda-forge capea `setuptools <82` contra nuestro piso `>=83`. Audit con el comando de CI sobre env fresco: 179 deps, verde |

## Retirados (Done verificado, 2026-09-23 — historia en git)

- **El CD dice "success" con la revisión nueva del gateway en crash loop**
  (propuesto 2026-09-18, `cd-gateway-health-fake-green.md`, recuperable con
  `git show cdecee9:.claude/backlog/cd-gateway-health-fake-green.md`) — Done
  2026-09-23 (v4.40.10). El step que hacía grep de `persona_gateway_starting` en 30
  líneas de log (la que se imprime ANTES del crash) se reemplazó por
  `scripts/cd_wait_revision.py`: exige que la revisión que carga la imagen NUEVA
  quede `Healthy` + `RunningAtMaxScale` + tráfico 100 sin ninguna réplica vieja
  corriendo al lado, y se pone rojo al instante ante `Failed`/`Unhealthy` (con los
  logs de esa revisión como evidencia), tras 90 s si ninguna revisión carga la
  imagen (el `az containerapp update` es continue-on-error y podía fallar en
  silencio), o al vencer 420 s. `khimeras-host` estrena el mismo gate — tampoco
  tenía ninguno. El arnés `tests/arch/test_cd_wait_revision_can_fail.py` corre el
  script contra listas de revisiones enlatadas por cada veredicto (el crash loop
  fundador incluido) y fija que `cd.yml` lo invoca para las dos apps min=1 y ya no
  contiene el grep. Recibo en prod: el primer run del CD con el gate es el de este
  mismo commit — ver su log para el `OK persona-gateway: revision … serves`.
- **Cadenas cortadas post-purga + código muerto** (propuesto 2026-07-14 por la
  autopsia de 10 agentes, `cadenas-cortadas-post-purga.md`, recuperable con
  `git show 1bb6f07:.claude/backlog/cadenas-cortadas-post-purga.md`) — la última
  acción que le quedaba se ejecutó el 2026-09-23 (v4.40.8): `class LLMShadowRouter`
  borrada de `demux_ai/llm_shadow_router.py` junto con su `_FakeLLM` y los 9 tests
  que eran su único constructor desde v4.21.82. **No se borró el módulo**: comparte
  archivo con `DirectAzureLLMRouter`, el router VIVO del host (`demux_ai/__main__.py`,
  `scripts/router_eval.py`), y con `_parse_target`/`_VALID_TARGETS`/`DEFAULT_TARGET`
  que consumen `dispatch.py` y tres arneses. Los cuatro comportamientos del parser
  que los tests muertos fijaban (match suelto, fallback `llm_unparseable`, primera
  línea con prosa, payload sin contexto byte-idéntico) siguen siendo conducta del
  router vivo y quedaron fijados sobre él. Definición de done cumplida:
  `grep -rn "LLMShadowRouter\|_FakeLLM" --include='*.py' demux_ai tests scripts` → 0.
  De las cinco cadenas del item: #1 y #2 murieron con su trigger, #3 se resolvió río
  arriba, #4 (corpus) lo cerró `6ba7a61` (#62) y su re-poblado vive en #61 (CLOSED
  09-19), #5 (consolidador) se borró el 08-06. `RouterBudget`, que el item daba por
  cero-callers, revivió como cap del router vivo en `72d5175`.
- **Graceful turn drain en deploys** (propuesto 2026-07-06, `graceful-turn-drain-on-deploy.md`,
  recuperable con `git show d02ae1d:.claude/backlog/graceful-turn-drain-on-deploy.md`) —
  su propio archivo decía **Done (2026-09-22)** desde `380a6c8` (v4.39.4, grace 45 en
  `persona-gateway`, declarado en `cd.yml`) y esta tabla lo seguía llamando *In
  progress*: la misma contradicción del índice que el 09-09 corrigió dos veces. Los
  tres pasos del item están hechos y verificados en `az` hoy: retry en el seam
  gateway→runner (v4.32.1 + reloj de 45 s v4.38.22), gate de recepción
  (`persona_gateway/drain.py`, v4.38.30, con el SIGTERM repetido arreglado en v4.39.0),
  y grace period: **45 s en `persona-gateway`, 600 s en `persona-runner`**
  (`terminationGracePeriodSeconds`, revisiones `--0000231` / `--0000245`;
  `khimeras-host` sigue en `null`, que es correcto — no sostiene turnos). Y lo que el
  item pedía "medir" quedó superado, no medido: el 09-23 el turno pasó a viajar por
  **boleto durable en las dos costuras** (v4.40.0–4.40.4, `robustness.md` § *El boleto
  es DURABLE*), probado en prod con tres experimentos — probe normal con el mismo
  `turn_id` en `invite_turns` y `turn_jobs`; **restart del gateway a media generación
  (17:02 UTC)** → la réplica nueva reanudó la fila al boot (`resumed=1`, `attempts=2`),
  el runner contestó `ticket_reused`, **una sola respuesta**; **restart del runner a
  media generación (17:06 UTC)** → el runner viejo terminó bajo el grace de 600, el
  poll lo recogió, **una sola respuesta**. Lo que sigue abierto de esta familia ya
  tiene sus propios items: el frío del runner (`min=0`) y la fase B (reattach a AIRE).

## Retirados (Done verificado, 2026-09-09 — historia en git)

- **AIRE gateway etapa 1: relay Anthropic** — Superseded por la etapa 2
  (2026-08-28) y **sin ninguna acción abierta**, contra lo que este índice decía.
  La fila afirmaba que *"`docs/runbook_dr.md:60-62` sigue listando los dos env
  vars muertos — pendiente"*. Falso: `grep -rn
  "ANTHROPIC_BASE_URL\|ANTHROPIC_CUSTOM_HEADERS" . --exclude-dir=.git` deja UN
  hit fuera del backlog, `docs/runbook_dr.md:58`, y esa línea dice justamente lo
  contrario — que las dos env vars *"ya no existen en la app: salieron en la
  revisión 195"*. `git show 1af6718 -- docs/runbook_dr.md` lo explica: **el mismo
  commit de la auditoría del 09-07 hizo la limpieza y su propio índice la dejó
  escrita como pendiente.** Env vivo de `persona-runner` confirmado hoy sin
  ningún `ANTHROPIC_*`: `POSTGRES_URL`, `PERSONA_RUNNER_TOKEN`,
  `ARTIFACT_BASE_URL`, `AIRE_GATE_URL`, `AIRE_AUTH_TOKEN`, `RUNNER_MCP_TOKEN`,
  `RUNNER_MCP_BASE`.

## Retirados (Done verificado, 2026-09-07 — historia en git)

- **runner-base: Node + Claude CLI + credencial OAuth muertos** — Done 2026-08-28,
  v4.35.2 (`c972579`), cerrado el mismo día que se propuso (`373eeb1` → `a81379e`).
  `runner-base.Dockerfile` borrado (`ls` 2026-09-07 → no existe; el runner monta
  `khimeras-base`), `CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_BASE_URL`/
  `ANTHROPIC_CUSTOM_HEADERS`/`TURN_BACKEND` fuera de la Container App (revisión
  195; hoy el env de `persona-runner` sólo lleva `AIRE_GATE_URL`+`AIRE_AUTH_TOKEN`
  como vars de LLM), rotador + regla del playbook actualizados; recibo vivo de
  Insult en #general con ᵛ⁴·³⁵·².
- **AIRE engine etapa 2: personas en casitas** — TERMINADA 2026-08-28, v4.35.0
  (`fc0944a`), hallazgos 1 y 2 cerrados con recibo vivo (`4cf04dd`, `e8e1e07`).
  La puerta engine es la única ruta: casita `{persona}-{canal}`, topic durable
  que rueda tras 1 h, judge en casita, las 10 tools de memoria por
  `/mcp/{casita}`. Verificado 2026-09-07: `grep -rn "claude_agent_sdk\|TURN_BACKEND"
  --include=*.py --include=*.yml .` → 4 hits, todos docstrings/comentarios de
  procedencia (`tooldef.py`, `test_tooldef.py`, `environment.yml`); las tres apps
  corren `798ba77` desde GHCR; `persona-runner` con `AIRE_GATE_URL=https://gate.bernarduriza.com`.
  Matiz del host: `2150ca0` (v4.36.0, 2026-08-29) migró la clase `HostRouterLLM`
  a `AIREBackend`, pero el host VIVO sigue arrancando `DirectAzureLLMRouter`
  (Azure OpenAI directo, `demux_ai/__main__.py:25`; el env de `khimeras-host` no
  lleva `AIRE_GATE_URL`) — `HostRouterLLM` sólo la construye `LLMShadowRouter`,
  que sólo construyen los tests.

## Retirados (Done verificado, 2026-08-06 — historia en git)

- **LLM shadow router / token bloat** — Done por partida doble. El token bloat se
  arregló en v4.21.82 (`716e1cd`, 9509→115 tokens con `DirectAzureLLMRouter`) y
  **el cutover a gpt-4.1 lleva LIVE desde el 2026-07-08** (`88481c9` v4.22.19:
  *"el cutover gpt-4.1 está LIVE"*), que además borró el shadow determinista
  (`demux_ai/shadow_router.py`) y su harness (`scripts/shadow_divergence_report.py`).
  Hoy el router ES el host: `demux_ai/__main__.py:25` → `run_host(DirectAzureLLMRouter())`
  en el Container App `khimeras-host` (Running, min=1). **El "26% de divergencia,
  falsos positivos peli/Netflix→vultur" que este índice citaba como NO-GO nunca
  existió: `diverged` era `target != "insult"`, o sea el NOMBRE del campo contando
  cada ruteo correcto a un hermano como divergencia.** La ventana A.2.3 quedó
  superada por la instrumentación de hoy: `host_dispatched` con
  `has_context`/`prev_target`/`switched` (v4.32.28-30) + `scripts/router_health.py`
  + `scripts/router_eval.py --no-context`, doctrinado en
  `.claude/rules/router-observability.md`.
- **Cross-turn durable research jobs** — Done v4.22.34 (`82ac0ff`, 2026-07-10),
  no "Proposed" como decía este índice: tabla `research_jobs`
  (`postgres_schema.sql:178`), marcador `[RESEARCH:]` → `save_research_job`
  (`persona_gateway/markers.py:135`) y `ResearchWorker.drain` que corre el job en
  el runner y postea el reporte de vuelta (`persona_gateway/workers/research.py`),
  con recuperación de jobs colgados.
- **ADN nivelado: bio + estilo + gustos propios** — Done 2026-07-16. Verificado:
  alice/vultur/frugivoro/unborn_being tienen `## Biografía` + estilo + "lo que sé
  sobre mí"; `persona_gateway/workers/reflection.py:78` escribe a `agent_facts`
  con `provenance="self_declared"`.
- **Dedup `persona.md` vs `insult.md`** — Done 2026-07-16. Verificado: `persona.md`
  raíz no existe y el tombstone `test_root_persona_md_stays_dead`
  (`tests/shared/test_registry_insult.py:32`) lo mantiene muerto.
- **Renombrar `vultur-gateway` → `persona-gateway`** — Done 2026-07-05 (v4.21.119
  `17fc427`). Verificado: `az containerapp list -g insult-rg` muestra
  `persona-gateway` (Running, min=1) y ningún `vultur-gateway`.

## Retirados (Done, 2026-07-05 — historia en git)

- addressed_to_sibling over-suppression — Done v4.21.113 `783b00d`; cross-talk @frugi E2E-verificado (`7a1f6d2`).
- runner no dispara invoke_alice → marcador `[INVITE:]` — Done v4.21.114 `3f871a5`, E2E verificado.
- mover runner a `persona_runner/` top-level — Done v4.21.118 `19db105`.
