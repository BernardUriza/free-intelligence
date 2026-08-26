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
