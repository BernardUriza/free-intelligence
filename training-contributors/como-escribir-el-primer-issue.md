# Cómo escribir el primer issue

La pieza que más pesa. Un issue mal escogido mata la sesión aunque el setup, la
herramienta y las ganas estén perfectas.

## Los cinco filtros

Un primer issue tiene que cumplir **los cinco**. Si falla uno, no es un primer
issue — puede ser trabajo real y valioso, pero no de arranque.

1. **Cabe en una línea de cambio real.** No "un archivo chico": una línea que se
   pueda señalar con el dedo, con su número.
2. **Se verifica en su propia máquina, sole.** Un comando, un verde. Sin
   credenciales que no tiene, sin infra, sin permiso de nadie.
3. **Tiene un resultado que se VE.** Algo observable en la superficie real
   después del deploy, no solo un test que pasa.
4. **No depende de nada que no controle.** Ni de una cuenta que no existe, ni de
   un servicio que hay que provisionar, ni de otra persona.
5. **El scope está cerrado por escrito, con lo que NO entra.** Si el repo tiene
   129 ocurrencias de la palabra que va a tocar, hay que decirle explícitamente
   que las ignore, o un `grep` la va a espantar.

## El caso que lo enseñó

**Issue #35 — failover de OAuth.** Escrito con cariño y bien explicado. Falla en
tres de los cinco filtros:

- Para verificarlo hay que **agotar a propósito el límite semanal de una cuenta
  Max**. No es verificable en su máquina.
- Requiere una **segunda cuenta Max que todavía no existía**. Depende de algo
  que no controla.
- Toca `session_pool`, inyección de token por proceso y reciclado de sesiones
  vivas. No es una línea.

Era trabajo real y sigue abierto. Pero como primer issue habría terminado la
sesión en frustración.

**Issue #36 — el alias `fruggy`.** Cumple los cinco:

- Una línea: `shared/personas/registry.py:133`.
- `pytest tests/shared/test_registry_insult.py` → verde, en su máquina, sin nada.
- Observable: escribir `fruggy, ¿el pan lleva huevo?` en `#general` y que el bot
  conteste.
- Cero credenciales, cero infra.
- Scope cerrado: no tocar `display_name`, ni el username de Discord, ni los ~129
  hits de "frugi" en el repo.

Resultado: PR verde a la primera y código en producción el mismo día.

## Cómo se ve un issue así por dentro

Estructura que funcionó (ver el #36 y el #38 como ejemplos vivos):

- **Para quién es** — que sepa que dirige, no que teclea. Y que preguntar es
  parte del rol, no una falla.
- **Qué está pasando** — el contexto contado como historia, con el síntoma real.
  Si hay un incidente concreto con hora, ponlo: un bug que pasó de verdad enseña
  más que un ejemplo inventado.
- **Qué queremos construir** — el comportamiento esperado, no la implementación.
- **Mapa del código** — los archivos y líneas exactas por dónde empezar, y
  **cuál test ya existente le está cuidando la espalda**. Ese detalle cambia la
  relación con el repo: no está sola, el repo se defiende.
- **Criterios de aceptación** — checklist que pueda tachar.
- **Qué NO entra** — explícito. Es lo que evita que se ahogue.
- **Cómo verlo funcionando** — el premio, descrito.

## Dale opciones reales, no un dictado

En el #36, Claude le ofreció tres tests de resistencia posibles con su
recomendación razonada y un "tú escoges". Escogió bien, y **escogió**. Un issue
que no deja ninguna decisión abierta produce a alguien que ejecuta pasos; uno con
una decisión real produce a alguien que entiende por qué.

## El segundo issue puede subir un escalón

El #38 (que Frugívoro razone la procedencia de los alimentos en vez de comparar
contra una lista) ya no es una línea de código: es **contenido y razonamiento**.
Sigue cumpliendo los filtros — un archivo, verificable, observable en Discord —
pero exige pensar, no solo editar.

Ésa es la progresión: de cambiar una línea, a cambiar cómo piensa una persona.

## Y el mejor issue es el que salió de la sesión anterior

El #38 nació de un bug que apareció **en vivo durante la sesión 1**: el bot
vegano recomendó sal de gusano. No hubo que inventar tarea. Cuando el trabajo
sale de algo que la persona vio pasar con sus ojos, no hay que explicarle por qué
importa.
