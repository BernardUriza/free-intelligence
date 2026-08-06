# Observabilidad del ruteo — el sesgo no se ve turno por turno

El host (`khimeras-host`) decide en cada turno QUIÉN contesta. Esta regla dice
cómo se diagnostica esa decisión, y por qué mirar turnos sueltos no sirve.

## La lección que la creó (2026-08-06)

Durante tres semanas el router mandó el **97.6% de los turnos a insult**
(331/339 en 30 días) y **nada estuvo rojo un solo minuto**. Cada turno logueaba
`reason=llm_insult` — un clean match del parser, que se lee como salud. No había
`llm_unparseable`, ni `content_filtered`, ni `router_fault`: ni un solo cero
fuera de lugar.

El defecto no era el parser cayendo al default. Era el cerebro **eligiendo a
ciegas**, porque la regla de máxima prioridad de su propio prompt
(`RULE 1 — CONTINUATION HOLDS THE FLOOR`) iba condicionada a un bloque de
conversación que no llegaba nunca. Se encontró leyendo el hilo de #general a
mano, no por una alarma.

**Un sesgo de ruteo es invisible turno por turno por construcción**: cada
decisión individual se ve razonable. Sólo aparece al agregar y comparar contra
un umbral. Por eso la instrumentación de abajo no es adorno.

## Primero corre el diagnóstico, no armes KQL a mano

```bash
python scripts/router_health.py              # últimos 7 días
python scripts/router_health.py --days 30
python scripts/router_health.py --days 1 --channel 1489180895264116736
```

Da veredicto con umbrales, no un volcado. Cinco bloques, cada uno contestando
algo que un turno individual no puede:

| Bloque | La pregunta | Cuándo se pone rojo |
|---|---|---|
| **SESGO** | ¿el cerebro elige, o contesta siempre lo mismo? | un target ≥90% |
| **CONTEXTO** | ¿los turnos llevan conversación o rutean a ciegas? | 0% = RULE 1 inalcanzable |
| **CONTINUIDAD** | ¿cuántos cambios de persona, y cuántos SIN contexto? | cambios ciegos > 0 |
| **PARSEO** | ¿el cerebro contesta la palabra sola o agrega prosa? | `_loose`/`unparseable` > 0 |
| **MUDEZ** | ¿se dispararon las ramas de fallo? | cualquier evento > 0 |

El umbral de sesgo (90%) es **el mismo que este repo ya usa para el anti-drift
de presets** ("flag si 90%+ de las clasificaciones son DEFAULT_ABRASIVE") — la
misma vacuna aplicada al router. El de fallback (5%) es la práctica de industria
para routers en producción.

## Los campos de `host_dispatched` y para qué existe cada uno

Desde v4.32.28 (`demux_ai/dispatch.py`):

| Campo | Para qué |
|---|---|
| `target` / `reason` | a quién fue y con qué calidad de parseo (`llm_x` limpio, `llm_x_loose`, `llm_unparseable`, `llm_content_filtered`, `router_fault`) |
| `has_context` | si el turno llevó conversación. **0% sostenido = RULE 1 muerta** |
| `context_lines` | tamaño real del bloque; si cae a 1-2, la ventana se está vaciando |
| `prev_target` | a quién fue el turno anterior de ese canal |
| `switched` | si esta decisión cambió de persona |

`host_mention_shortcircuit` lleva además `fanout` (cuántas personas despertó una
frase) y su propio `prev_target`. **Separa siempre los turnos por mención de los
ruteados**: el bypass no pasa por el cerebro, y mezclarlos contamina cualquier
tasa de sesgo.

### La consulta que importa: cambios de persona a ciegas

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(7d)
| where ContainerAppName_s == "khimeras-host"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "host_dispatched"
| where tobool(p.switched) == true and tobool(p.has_context) != true
| project TimeGenerated, de=tostring(p.prev_target), a=tostring(p.target), reason=tostring(p.reason)
```

Cada fila es un candidato a **secuestro de continuación**: un turno que cambió
de persona sin que el cerebro supiera quién traía el hilo. El caso fundador
—`explica mejor lo del extractor 24/7` yéndose a frugivoro tras tres turnos de
Insult— es exactamente esta forma.

## Un cero NO prueba salud — puede ser una rama que no puede sonar

La trampa más cara de esta familia (Rule 22 del playbook: *el signal que no puede
fallar no prueba nada*). Tres casos reales, todos el mismo día:

1. **`RULE 1`** del prompt, condicionada a un bloque que nadie proveía.
2. **`recovered_without_context=True`** (bf67e08): reintentaba sin contexto
   cuando Azure filtraba el prompt — **inalcanzable**, porque nunca había
   contexto que quitar. Su cero en KQL no significaba "no pasó", significaba "no
   puede pasar".
3. **`effort`**: el prompt le prometía al modelo que definía su tiempo de
   trabajo, y el valor **no tenía un solo consumidor**. Una mentira al modelo y
   razonamiento gastado en una decisión que se tiraba. **Borrado de los dos
   lados el mismo día** (v4.32.30) en vez de parkeado — un valor sin consumidor
   es deuda, no una feature en pausa. Si vuelve, vuelve CON su consumidor en el
   mismo PR.

**Antes de leer un cero como salud, pregunta: si esto estuviera roto ahora mismo,
¿este contador podría subir?** Si la respuesta es no, el contador es decorativo.

El arnés que cierra la clase es `tests/arch/test_routing_prompt_promises_are_kept.py`:
si el prompt promete algo (un bloque de contexto, un target válido), el código tiene que proveerlo o consumirlo, demostrable en CI. Es
primo de `test_every_counted_event_has_a_live_emitter` (contadores oyendo eventos
sin emisor) y de [[migrations-end-with-deletion]]: **la promesa sobrevive al
mecanismo que la cumplía, y nadie se entera porque nada se pone rojo.**

## El eval offline mide el ruteo sin esperar tráfico

`scripts/router_eval.py` corre el gpt-4.1 real contra mensajes REALES de
#general, reconstruyendo el contexto exacto de producción.

```bash
# el set de regresión congelado — re-córrelo tras tocar host_routing.md
python scripts/router_eval.py --limit 30 --until 2026-07-09T04:11:00Z
python scripts/router_eval.py --limit 30 --until 2026-07-09T04:11:00Z --no-context
python scripts/router_eval.py --limit 30 --dry-run    # cero gasto
```

`--no-context` es el contrafactual: mide **qué aporta el contexto** corriendo el
mismo set en ambas condiciones. Medido el 2026-08-06 con el prompt ya sin
`effort`: **13.3% sin contexto → 16.7% con contexto**, +26% de tokens de entrada,
cero latencia añadida, y el desahogo personal sigue protegido ("presión
invisible" se queda en insult en ambas condiciones).

Los 5 ruteos con contexto son 4 frugívoro legítimos + 1 mención explícita: cero
falsos positivos. Antes de borrar el `effort` el mismo set daba 10.0% → 20.0%,
pero uno de esos 6 era sobre-ruteo ("Holii, si hay que ver peli" → vultur, que es
coordinación social, no petición de crítica) y se corrigió solo al simplificar el
prompt a una palabra. **Menos ruteos y mejores.**

**El reparto no es el veredicto.** Cada ruteo a un especialista se revisa a mano:
¿el mensaje PEDÍA a esa persona, o sólo mencionaba su tema? En la corrida
fundadora, 2 de 3 cambios eran recuperaciones legítimas y 1 era sobre-ruteo.

Requiere que tu IP esté en el firewall del Postgres (`az postgres flexible-server
firewall-rule create ...`, patrón `claudecode-<ip>` en `insult-rg`).

## Orden de diagnóstico cuando "la persona equivocada contestó"

1. **`scripts/router_health.py --days 1`** — ¿es un caso suelto o un sesgo?
2. **KQL del turno concreto** (`host_dispatched` en esa ventana) — mira `reason`,
   `has_context`, `prev_target`. `llm_x` limpio significa que el modelo lo
   ELIGIÓ; `router_fault` / `llm_unparseable` significa que se cayó al default.
   **Son diagnósticos opuestos: no los confundas.**
3. **El hilo real en #general** — lee lo que de verdad se dijo antes. Una persona
   que abre justificándose ("te lo pinto en mi vocabulario…") está compensando un
   mal ruteo, y es la mejor pista de que el cerebro no sabía quién traía el hilo.
4. **Reproduce en banco** con `router_eval.py --limit 1 --until <justo después>`
   en ambas condiciones, antes de tocar el prompt.

Nunca toques `host_routing.md` sin re-correr el set congelado: es el único
freno contra arreglar un caso y romper tres.
