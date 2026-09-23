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
| `budget_exhausted` | el CLIENTE pooled cruzó su techo (`AIRE_MAX_BUDGET_USD=$1` acumulado del cliente, NO por turno) y el turno se cortó. **Desde 2026-09-03 solo el slot METERED nace con el cap** (aire-server `options.build_options` + `ledger.account`): un cliente OAuth corre sin corte, porque cortarlo cada ~3 turnos `crisis` de Alex solo compraba un cache-creation por renacimiento | el runner conserva la respuesta si ya llegó (el corte viene DESPUÉS del result) y si no, reenvía UNA vez — AIRE mismo receta "send the turn again to continue" |
| `budget_exceeded` | el techo de proceso (`AIRE_MAX_SPEND_USD=$20`) se agotó | solo puede dispararse en el slot METERED (api-key-fallback); un ledger agotado ya NO bloquea turnos OAuth |
| `credentials_exhausted` | toda la cadena de credenciales enfrió (weekly limits) | sin cambio: terminal, 500, espera el probe horario |
| *(sin código)* `agent_runner_client_zero_generation` con `text_preview: "You've hit your session limit · resets …"` y `model: <synthetic>` | el slot OAuth pegó con el **límite de sesión de 5 h del Max** y AIRE lo dejó pasar como turno exitoso: el rotor solo reconocía `weekly|usage limit`, así que no giró a `api-key-fallback` | aire-server `LIMIT_PHRASE` reconoce `session` desde 2026-09-03 (medido en vivo 22:47 UTC: dos veces seguidas, el host reintentó sobre el mismo slot y publicó su fallback). Con el fix el slot enfría 1 h y el turno gira a la tarjeta, con su cap de $1 |

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

Los dos lados del fix: aire-server `39f9d9e` + `724f961`; server-bot
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

## El rotor de credenciales y el plan de las DOS cuentas Max $200 (2026-09-08)

Cuando "todas las personas mudas" y KQL muestra `agent_runner_client_zero_generation`
con `text_preview: "Credit balance is too low"` — el Max topó su rate limit y el
rotor cayó al slot de tarjeta, que está en cero. Verificado el 2026-09-08: probar
el OAuth token directo contra `api.anthropic.com/v1/messages` devuelve
`rate_limit_error` → el tope es de la CUENTA, no del token; un restart limpia el
cooldown en RAM pero el Max se re-exhausta al siguiente turno.

**Desde aire-server `33b8f26` (2026-09-08) ese texto ya no sale como prosa:** el
rotor reconoce `credit balance is too low` y `rate_limit_error` como slot quemado
(igual que `hit your … limit`), y el cooldown lee el reset que trae el aviso
(*"resets 11:20pm (UTC)"* / *"resets Sep 10, 8pm (UTC)"*) en vez de la hora plana.
Con todos los slots secos el turno muere con `credentials_exhausted` real y el host
habla por la casa. Lo que sigue viéndose como `zero_generation` con ese texto en
KQL es una revisión anterior al deploy de ese commit, o un gateway sin el fix.

**El rotor** (`aire-server` `server/aire/engine/credentials.py`, `CHAIN`) tiene tres
slots en orden fijo, y arma solo los que tengan su env presente:

| Slot | Env que lee | Es metered |
|---|---|---|
| `oauth-primary` | `CLAUDE_CODE_OAUTH_TOKEN` | no (Max, costo nominal) |
| `oauth-backup` | `CLAUDE_CODE_OAUTH_TOKEN_BACKUP` | no (Max) |
| `api-key-fallback` | `ANTHROPIC_API_KEY_FALLBACK` | **sí (tarjeta real)** |

Un `oauth-backup` con un token de la MISMA cuenta que el primary NO compra nada: el
rate limit es de la cuenta, así que topan juntos. Solo sirve un token de OTRA cuenta.
Y `claude setup-token` **revoca** el token anterior de esa cuenta (SSOT
`~/.secrets/claude-max-oauth.txt`: "un solo token activo por cuenta").

**Las dos cuentas de Bernard (2026-09-08):**
- `bernarduriza@gmail.com` (org `d1c8c86b`) — Max **$100**, es el `oauth-primary` del
  bot (token `0bb5…` compartido por server-bot/aire/og118).
- `vegdevida@gmail.com` (org `8e661957`) — Max **$200 (20x)**, verificado 2026-09-08
  vía `claude.ai/api/organizations` (tier `default_claude_max_20x`); es la cuenta
  logueada en el Chrome de debug. **No hay token suyo guardado** en `~/.secrets/` —
  se genera con `claude setup-token` logueado en vegdevida (login/2FA = átomo de
  Bernard) cuando toque el escalonamiento.

**El plan de Bernard:** tener las DOS en Max $200, con los ciclos DESFASADOS (que no
"inicien el mismo día"). Para escalonarlas quiere dejar topar AMBAS alrededor de un
miércoles/jueves y ahí pagar el upgrade a $200 en fechas distintas. Por eso el bot
mudo ahorita es PARTE del plan — NO meter el `oauth-backup` ni revivir el bot antes
de tiempo, porque eso arruina el escalonamiento (dont-override-his-architecture).

**Cuando toque ejecutar (el mié/jue):** sacar el OAuth token de la segunda cuenta
$200, meterlo como `CLAUDE_CODE_OAUTH_TOKEN_BACKUP` en `/etc/aire/env` (consumir a
variable, nunca `cat` — es secret-bearing), `systemctl restart aire-server`, y
verificar con un turno real en #general que el rotor cae al backup cuando el primary
topa. Ojo con la distinción que NO está verificada: el ciclo de BILLING (mensual) y
las ventanas de RATE LIMIT (5h de sesión + semanal, que resetean por USO) son relojes
distintos — escalonar el billing no desfasa por sí solo cuándo topan los límites.

---

**Actualización 2026-09-17 (sesión aire-server):** el `oauth-backup` de AIRE quedó
ARMADO, pero con una TERCERA cuenta, no con vegdevida. Bernard entregó un token de
`bernardurizadev@gmail.com` (org `7b946828`) — cuenta distinta del primary, pool
separado, probado vivo (`200`/PONG contra `api.anthropic.com/v1/messages`). Guardado
etiquetado en `~/.secrets/aire-claude-oauth-backup.txt`, metido a `/etc/aire/env` del
droplet, `aire-server` reiniciado, y verificado en `/health` con door token: **3 slots
armados** (`oauth-primary`, `oauth-backup`, `api-key-fallback`), `credential_failover:
true`.

Esto SUPERSEDE el "NO meter el oauth-backup antes de tiempo" de arriba: esa regla era
para el escalonamiento bernarduriza↔vegdevida del BOT de discord; AIRE es otro servicio
y Bernard lo ordenó hoy explícitamente. **El plan de escalonamiento vegdevida/$200 sigue
vigente y separado** — bernardurizadev es una 3a cuenta que no lo toca. (Tier de
bernardurizadev no verificado: el token dispatcha, pero si es Pro y no Max su pool es
menor que un Max — pendiente menor.)

**La card (`api-key-fallback`) SIGUE a $0** — probado el 17-sep contra la API:
`400 "Your credit balance is too low"`, idéntico al 8-sep. Es el 3er slot (solo se usa
si caen los DOS OAuth, pools separados → improbable a la vez), así que hoy es red
terciaria; pero `credential_failover: true` la cuenta como slot válido. Para cerrarlo
del todo: recargar créditos en la cuenta de la card, o borrar
`~/.secrets/aire-api-key-fallback.txt` para que el rotor no cuente una red falsa.
