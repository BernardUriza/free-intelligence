# Los presupuestos de AIRE — cuando "los bots se mueren sin explicación", busca `budget_*` primero

El P1 del 2026-08-25/26: todas las personas mudas ~16 horas (14:26 → 06:48 UTC)
y muertes "aleatorias" sueltas el resto del día, sin nada rojo en Azure. La
causa nunca estuvo en este repo ni en Discord: eran los DOS techos de gasto de
AIRE (`aire-server`, el droplet), matando turnos con dólares NOMINALES que la
suscripción Max ya había pagado.

## La familia de errores y qué significa cada uno

Todos llegan como `aire_route_turn_failed` en KQL (persona-runner), con el
código dentro del texto del error:

| Código | Qué pasó | Desde 2026-08-26 |
|---|---|---|
| `budget_exhausted` | el CLIENTE pooled cruzó su techo (`AIRE_MAX_BUDGET_USD=$1` acumulado del cliente, NO por turno) y el turno se cortó | el runner conserva la respuesta si ya llegó (el corte viene DESPUÉS del result) y si no, reenvía UNA vez — AIRE mismo receta "send the turn again to continue" |
| `budget_exceeded` | el techo de proceso (`AIRE_MAX_SPEND_USD=$20`) se agotó | solo puede dispararse en el slot METERED (api-key-fallback); un ledger agotado ya NO bloquea turnos OAuth |
| `credentials_exhausted` | toda la cadena de credenciales enfrió (weekly limits) | sin cambio: terminal, 500, espera el probe horario |

## La ley que salió del incidente (vive en aire-server)

**Un techo de gasto protege DINERO, no uso.** La cadena de credenciales de AIRE
es oauth-primary (Max, costo marginal $0) → oauth-backup → api-key-fallback
(tarjeta real). El SDK reporta `total_cost_usd` igual en todos los slots, y el
ledger contaba esos dólares nominales contra $20 de vida del proceso → mudez
global cada ~2 días ($24.25 nominales en 2.5 días medidos), "curada" por
cualquier restart. Desde aire-server `39f9d9e`/`724f961`:

- El ledger RAM y `month_to_date()` (la cifra que costwatch alarma) cuentan
  SOLO gasto metered (`credentials.is_metered`); lo nominal se registra entero
  en `aire_spend` (columna `metered`) pero no mata turnos ni pinta alarmas.
- El gate vive en `run_turn` por-slot: agotado el ledger, los turnos OAuth
  siguen sirviendo y solo el slot que cobraría a la tarjeta se rechaza.

## Orden de diagnóstico para "bot mudo" (antes de tocar nada)

1. KQL: `aire_route_turn_failed` en la ventana — si el error trae `budget_`,
   ya sabes el sistema culpable (el droplet, no este repo).
2. Estado del droplet: `ssh -i ~/.ssh/aire_vm root@159.203.84.13`, techos en
   `/etc/aire/env` (consumir a variable, NUNCA cat — es secret-bearing),
   restarts con `systemctl show aire-server -p ActiveEnterTimestamp`.
3. Un `agent_runner_starting` frecuente en KQL NO es un crash loop del runner:
   persona-runner tiene `min=0` y eso son cold starts de scale-to-zero.

Los dos lados del fix: aire-server `39f9d9e` + `724f961`; discord-bot
v4.32.81. Tests que fijan la clase: aire-server `test_ledger_metered.py` +
`test_spend.py` (metered), acá `test_aire_route.py` (reenvío único) y
`test_aire_backend.py` (el corte no anula la respuesta entregada).

## El "…" del corte de presupuesto — la respuesta que "se entregaba" nunca llegó (2026-09-03)

El fix del 26-ago fue fake-green en su mitad más visible. fi-runner conservaba
la respuesta del turno que cruza `AIRE_MAX_BUDGET_USD` (warning *"AIRE cut the
client at its budget ceiling after the result… the answer is delivered"*) —
pero **Discord mostraba "…"**. Ocho veces en dos días, todas a Alex, cero rojo.

La cadena, con recibo en cada eslabón:

1. El SDK (0.2.123) deja terminar la llamada que cruza `max_budget_usd`, streamea
   el texto, y devuelve el `ResultMessage` con `subtype=error_max_budget_usd` y
   **usage en ceros** (reproducido local con Haiku y cap de $0.0115).
2. AIRE (`engine/drain.py`) tomaba ese usage tal cual → `output_tokens: 0`.
3. persona-runner (`aire_route.py`) hacía `int(usage.get(k, 0) or 0)` — un
   usage ausente también se volvía un cero EXPLÍCITO.
4. El gateway (`agent_client.py`, guard del 401-como-prosa del 19-jul) lee
   texto + `output_tokens == 0` como *"text no model ever generated"* →
   `agent_runner_client_zero_generation` → `PersonaTurnError` → "…".

**El tell en KQL:** cada `agent_runner_client_zero_generation` del gateway con
`model=claude-opus-4-7, stop_reason=end_turn` cae en el MISMO segundo que un
*"AIRE cut the client"* en persona-runner. Son las víctimas de Alex porque sus
turnos (tier `crisis`, cache de ~90k tokens) son los que empujan al cliente por
encima del $1 acumulado.

El fix, dos capas: aire-server suma el usage que SÍ traen los `AssistantMessage`
y lo reporta cuando el result lo niega (+ `subtype` en el `TurnResult`,
`test_drain_budget_cut.py`); persona-runner manda `null`, nunca `0`, cuando
AIRE no reportó un conteo (`reported_tokens`, v4.37.4). El guard del gateway
no se toca: acusar por un cero explícito sigue siendo correcto.

**Lección:** "la respuesta se entrega" se verifica donde la lee el humano
(#general), no en el test unitario del cliente que la conserva. Un fix de
entrega sin probe en Discord es un fix sin verificar.
