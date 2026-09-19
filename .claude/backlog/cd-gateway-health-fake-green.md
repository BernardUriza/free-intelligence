# El CD dice "success" mientras la revisión nueva del gateway crash-loopea

Status: Proposed
Proposed: 2026-09-18 by Claude (hallazgo del P0 de Bernard)

## What it is
Del 2026-09-17 (af436de, v4.38.32) al 2026-09-18 (6cc4612, v4.38.46), toda revisión nueva
de `persona-gateway` murió al arrancar (`TypeError: Config.__init__() got an unexpected
keyword argument 'install_signal_handlers'`). ACA dejó vivo el `persona-gateway--0000212`
(v4.38.31) con 0% de tráfico nominal, y el CD reportó **success** en cada run
(98a4b545, 01aeadb6). Nadie se enteró hasta ver un `ᵛ⁴·³⁸·³¹` viejo en las respuestas.

El health check de startup del CD (`persona_gateway_starting`) no puede fallar:
esa línea se loguea antes del crash.

## Canonical path to reuse (Art. 6)
Mismo contrato que ya usa el CD: después del deploy, exigir que la revisión NUEVA esté
`healthState=Healthy` + `runningState=RunningAtMaxScale` y que sea la única activa
(`az containerapp revision list ... --query "[?properties.active]"`). Si no, rojo.

## Status / next step
El crash se arregló en 6cc4612, con un test que construye el server con uvicorn de verdad
(`tests/core/test_gateway_invite_server_signals.py`). Falta endurecer el step del CD.
