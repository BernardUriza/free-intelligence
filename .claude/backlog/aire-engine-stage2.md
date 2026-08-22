# AIRE engine — etapa 2: el runner deja de hostear el SDK y las personas viven en casitas

Status: **Flag shipped, OFF en prod; la ruta vieja SIGUE VIVA** (2026-08-22).
El código de la ruta AIRE está en `main`, con tests, detrás de
`TURN_BACKEND=aire`, cuyo default es `local`. **Nada está migrado** — ni un
turno de producción ha salido por la puerta engine. Verificación en vivo y
decisión de encender: de Bernard.
Proposed: 2026-08-22 (orden de Bernard: "etapa 2, NO hoy") · Construida: 2026-08-22

## Qué es

La migración real: `persona-runner` deja de ser un host propio del Claude Agent
SDK y cada turno se vuelve un
`POST /projects/{p}/sessions/{s}/messages` contra la puerta ENGINE de AIRE. El
precedente es og118 (free-intelligence), migrado 2026-08-21 — pero og118 era un
runner delgado; éste no.

## El diseño, ya decidido (no reabrir)

| Fork | Decisión |
|---|---|
| Alcance de la casita | **persona+canal**: `{persona_id}-{channel_id}` |
| Dónde vive el ADN | casita BASE por persona (`insult`), instalada vía `/init`; cada casita de chat nace THIN con el stub `@base insult` que AIRE dereferencia en cada spawn (aire-server `ef21e68`) |
| Playwright | **SE CAE** en la ruta AIRE (droplet de 512MB, presupuesto duro de $20 — [[do-budget]] de aire-server) |
| WebSearch/WebFetch | sobreviven vía `mode=agent` (dial server-side de AIRE) |
| facts + `behavioral_guidance` | viajan **IN-BAND**, compuestos en el mensaje del turno como ya se compone `turn_context`. **Ninguna credencial de Khimeras llega al droplet** |
| tools del registry | `["persona","memory"]` en cada turno |
| `/v1/judge` | `mode=complete` en la casita utilitaria `{persona_id}-judge`, sesión desechable por llamada |
| errores terminales | `budget_exhausted` / `credentials_exhausted` → 500 (el gateway usa su error neutral en personaje); `slot_busy` → 503 (reintento transitorio). **Un turno cortado JAMÁS se ve como éxito** |

## Qué se construyó (en `main`, detrás del flag)

| Archivo | Qué es |
|---|---|
| `persona_runner/engine/aire_backend.py` | El cliente canónico de la puerta, **VENDOREADO** desde `fi_runner/backends/aire.py` (free-intelligence `b99a26ba`, PR #413). Vendoreado y no importado porque **ningún fi-runner publicado lo trae**: el canal de conda tope 0.17.1 no empaqueta `backends/aire.py` y este repo pinnea `fi-runner=0.11.0` |
| `persona_runner/engine/aire_route.py` | La ruta: casitas, pre-fetch de facts, guard de capacidades, mapeo de errores, judge |
| `persona_runner/api/turn.py` · `api/judge.py` | La bifurcación por `TURN_BACKEND` |
| `persona_runner/runner.py` | El boot verifica la ruta que DE VERDAD va a servir turnos |
| `core/config.py` · `core/schemas.py` · `engine/framing.py` | El flag, `JudgeRequest.persona_id`, el bloque `<user_memory>` |
| `tests/agent/test_aire_{route,backend}.py` · `test_turn_backend_flag.py` | 44 tests; el default `local` está pinneado por test |

## Los hallazgos que BLOQUEAN encender el flag

Ninguno se sabía al proponer el item. Los dos primeros son de AIRE (cada uno =
un endpoint/capacidad que le falta a `aire-server`); el tercero es de este repo.

### 1. 🔴 AIRE ignora el `model` en una sesión CALIENTE (medido en vivo)

Probado el 2026-08-22 contra `https://gate.bernarduriza.com`, dos turnos en una
sola sesión:

```
requested: claude-haiku-4-5-20251001  → answered: claude-haiku-4-5-20251001
requested: claude-sonnet-4-6          → answered: claude-haiku-4-5-20251001
```

Sin error y sin aviso: el campo simplemente se ignora. Causa raíz en
`aire-server/server/aire/engine/core.py::_client_for` — las opciones (mode,
tools **y model**) se construyen sólo en un **pool miss**, así que un cliente
caliente conserva la forma con la que nació durante ~55 min
(`AIRE_POOL_IDLE_S=3300`).

**Qué significa aquí:** el `routing/` de este repo elige modelo POR TURNO
(Haiku/Sonnet/Opus por severidad + presupuesto Opus 24h). Por la puerta AIRE ese
ruteo degrada a *"el modelo con el que arrancó la sesión"* — una escalada a Opus
por un turno severo la contestaría Haiku, en silencio, hasta una hora.
`aire_route.model_diverged` loguea `aire_route_model_not_honoured` cada vez, así
que deja de ser invisible; **pero el ruteo sigue roto hasta que AIRE pueda
rebindear.** El judge NO sufre esto: sesión desechable por llamada = cliente
nuevo = modelo honrado.

**Hueco de AIRE:** la puerta necesita rebindear el `TurnSpec` cuando cambia
(o un `?rebirth=1` / `DELETE .../client` que fuerce el renacimiento del cliente).

### 2. 🔴 La personalidad pierde 9 de sus 10 tools de memoria

La ruta local monta `persona_memory` (in-process, contra el Postgres de
Khimeras) con diez tools. En AIRE sólo existen las del registry vetado
(`persona`, `memory`). Inventario honesto:

| Tool local | En la ruta AIRE |
|---|---|
| `get_user_facts` | ✅ **compensado**: el runner lo pre-consulta y lo compone in-band como `<user_memory>` |
| `get_recent_messages` · `search_messages` · `deep_memory` | ❌ perdidas. El tool `memory` de AIRE recuerda **su propio transcript** (por casita), no el historial de mensajes ni la búsqueda vectorial de Khimeras |
| `get_disclosure_log` · `get_emotional_arc` | 🔴 **perdidas — y son la superficie clínica**: fase del arco emocional y registro de revelaciones. Es exactamente lo que protege a un usuario vulnerable. No diluir esto es la orden; hoy la ruta AIRE lo diluye |
| `get_agent_facts` · `add_agent_fact` · `update_agent_fact` | ❌ perdidas (self-facts). El tool `persona` de AIRE edita la persona viva y las cubre **en parte** |
| `publish_html_artifact` | ❌ perdida |

**Un lado bueno, real:** al pre-componer los facts, el modelo ya no puede
*pedir* memoria de nadie — la identidad la pone el servidor, siempre. El
incidente del 2026-08-10 (atribuirle a Bernard un fact de Alex) es
estructuralmente imposible por esta ruta.

**Hueco de AIRE:** el registry necesita un tenant que hable con una base AJENA
al droplet — o el fork que el item original ya nombraba (un MCP HTTP hosteado
por ESTE repo que AIRE sólo cablea). Mientras tanto, las dos tools clínicas
tendrían que viajar in-band como los facts.

### 3. 🟡 La superficie de builtins NO es la misma, y este repo no puede imponerla

`FORBIDDEN_BUILTIN_TOOLS` de este repo = Bash/Write/Edit/NotebookEdit/Task. El
`mode=agent` de AIRE (auditado contra `engine/options.py::MODES` en `ef21e684`)
concede `Read, Write, Glob, Grep, WebSearch, WebFetch` y sólo deniega `Bash`.

**Aceptado, no escondido**, sobre dos hechos verificados: el hook `PreToolUse` de
`aire-server/engine/cage.py` deniega cualquier tool de archivos que resuelva
fuera de la casita, y **el droplet no tiene ninguna credencial de Khimeras** —
`POSTGRES_URL` y el OAuth de la flota nunca salen de este contenedor, así que la
amenaza del 2026-08-10 (una shell donde están los secretos) no se traslada.
`aire_route.AUDITED_MODE_{ALLOWS,DENIES}` guarda la auditoría y el boot truena si
NUESTRA config se desvía; **un cambio del lado del droplet es invisible aquí**
hasta re-auditar. Se loguea `aire_route_accepted_tool_delta` en cada boot.

**Hueco de AIRE:** la puerta no ofrece denylist de builtins por turno.

### 4. Huecos menores de AIRE (cada uno = un endpoint que falta)

- **No hay sonda de "¿existe esta sesión?"** por HTTP (`Engine.has_session`
  existe adentro; no está expuesta). Por eso el fold de historia se gobierna con
  un `set` en RAM: tras un reinicio del runner, la memoria de AIRE sobrevive pero
  nuestro set no, y el primer turno vuelve a plegar historia que la sesión ya
  tiene. Duplicación acotada, aceptada; el endpoint la mata.
- **La puerta no acepta bloques de documento/PDF** (`engine/vision.py` sólo
  valida imágenes). Los attachments no-imagen se **cuentan** y se loguean
  (`aire_route_attachments_dropped`), nunca se pierden en silencio.
- **Latencia sin medir**: Discord → Azure → droplet DO → Anthropic contra el
  actual Azure → Anthropic. Los turnos de voz/TTS son los sensibles. Medir antes
  de encender.

## El cableado (env fuera de banda, como la etapa 1)

El código lee la puerta del entorno; **jamás de un archivo del repo**:

- `TURN_BACKEND=aire` — enciende la ruta (default `local`)
- `AIRE_GATE_URL=https://gate.bernarduriza.com`
- `AIRE_AUTH_TOKEN` — Bearer de la puerta engine (o `AIRE_CANARY_TOKEN`)
- `AIRE_TURN_MODE=agent` (default; cualquier otro modo TRUENA el boot)
- `AIRE_FACTS_MAX_CHARS=6000` (default)

Documentado en `docs/runbook_dr.md` § orden de reconstrucción, paso 4, con la
misma forma que dejó la etapa 1.

**Qué token va ahí es decisión de Bernard, no del agente.** El
`~/.secrets/aire-canary-token.txt` dice textualmente *"consumer: aire-front on
Azure"*, y `aire-llm-token.txt` dice *"Only Bernard has this"*. Ninguno nombra a
`persona-runner`, así que ningún agente lo despliega por su cuenta
([[credential-scope-is-the-named-surface]]). Encender:

```bash
az containerapp secret set -n persona-runner -g insult-rg \
  --secrets aire-auth-token=<el token que Bernard elija>

az containerapp update -n persona-runner -g insult-rg \
  --set-env-vars TURN_BACKEND=aire \
                 AIRE_GATE_URL=https://gate.bernarduriza.com \
                 AIRE_AUTH_TOKEN=secretref:aire-auth-token
```

Apagar (rollback, una revisión):

```bash
az containerapp update -n persona-runner -g insult-rg \
  --remove-env-vars TURN_BACKEND AIRE_GATE_URL AIRE_AUTH_TOKEN AIRE_TURN_MODE
```

## El paso de BORRADO (el flag es andamio, no permiso de estacionamiento)

Por [[migrations-end-with-deletion]]: mientras la ruta vieja viva, **está
prohibido escribir "migrado"** en cualquier reporte de este item. La redacción
honesta es la de arriba: *flag shipped, old path alive*.

Cuando Bernard declare permanente el flag, en el MISMO PR mueren:

1. `persona_runner/engine/session_pool.py` — el pool local de `ClaudeSDKClient`
2. `persona_runner/engine/options.py` — `build_options` y el árbol de
   `ClaudeAgentOptions` (`verify_required_tools` sobrevive sólo si algo lo usa;
   si no, muere con él y `aire_route.verify_audited_surface` queda de guard)
3. La rama local de `api/turn.py` y `api/judge.py`, y el flag `TURN_BACKEND`
   entero de `core/config.py`
4. `persona_runner/mcp_tools/` — los servers in-process — **sólo si** el hueco 2
   se cerró; hasta entonces NO se borran, se migran
5. Las specs de Playwright en `options.py` y la dep `@playwright/mcp` del
   Dockerfile
6. `persona_runner/engine/aire_backend.py` muere aparte, el día que un
   fi-runner ≥0.19 con `AIREBackend` + thin birth llegue al canal de conda:
   `aire_route` pasa a `from fi_runner.backends.aire import AIREBackend`

**Criterio de terminado (el grep, no el relato):** las tres salidas vacías, en
el reporte, textuales.

```bash
grep -rn "session_pool\|build_options\|TURN_BACKEND" persona_runner/ tests/   # 0
grep -rn "claude_agent_sdk" persona_runner/                                   # 0
grep -rn "playwright" persona_runner/ Dockerfile.* environment.yml            # 0
```

Un PR que mueva código sin borrados en el diff no es una migración y no se llama
así.

## Camino canónico reusado (Art. 6)

- og118 (free-intelligence PRs #410–#413) como plantilla del cliente del engine
  door — `AIREBackend` vendoreado tal cual, con cuatro adaptaciones marcadas.
- aire-server #36 (`@base` / casita THIN) para el persona.md como CLAUDE.md vivo.
- El registry de tools de AIRE (#29/#36) para los tenants MCP.

## Siguiente paso

Un turno REAL de Discord por la puerta engine, mirado en vivo, antes de nada más.
Los huecos 1 y 2 son de Bernard: el 1 pide trabajo en `aire-server`, el 2 es un
fork de arquitectura (¿tenant del registry con credencial ajena, o MCP HTTP
hosteado aquí?). La etapa 1 ([[aire-gateway-stage1]]) ya da el espejo sin nada de
esto — no hay prisa técnica.
