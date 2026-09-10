# PERSONA-SSOT-2 — el personaje vive DOS veces, y el elemento que lo cita no lo lee

Status: **Done 2026-09-10** — Bernard decidió: el prompt de un elemento vive en discord-bot y en ningún otro lado. Vultur borrado de aquí, Reaper migrado allá, `fi-personas` eliminado y la capacidad local arrancada del código. Ver el cierre al final
Proposed: 2026-09-09 by Bernard (preguntó dónde debe vivir el prompt de un elemento: en el bot o en og118)

## El estado real, medido

`elements_registry.py:25` declara **PERSONA-SSOT-1**: *"a persona's shared CORE
lives once in the fi-personas package, consumed by every surface that speaks it
(og118 element, **the Discord bot**), so the character is not copied per repo."*

Eso último no ocurre. Verificado:

| | |
|---|---|
| `apps/packages/fi-personas/personas/vultur.core.md` | 96 líneas, **con** el marcador `<!-- CONTEXTO_OPERATIVO -->` |
| `discord-bot/shared/personas/vultur.md` | **205 líneas** |
| Líneas en común | 77 |
| Sólo en discord-bot | **87** |
| ¿discord-bot importa `fi-personas`? | **no** — cero referencias en todo el repo |

El core es un SUBCONJUNTO de la copia que de verdad se usa en Discord. Se extrajo
una vez y la copia siguió creciendo sola. Cambiar la voz de Vultur hoy son dos
ediciones en dos repos, que es exactamente lo que la doctrina se escribió para
evitar.

## El defecto de esquema que lo permite (y es lo que hay que arreglar primero)

El registry deja que un elemento declare **las dos cosas a la vez**, y Oxígeno lo
hace: `engineBinding.kind = external_http_engine` **y** `personaCorePath` +
`personaPromptPath`.

Cuando eso pasa, lo local queda muerto en los dos sentidos:

- **No se ejecuta.** `app.py:242` retorna en la rama externa antes de llamar a
  `composed_persona()`.
- **No se valida.** Los checks de persona viven dentro del `if not external` de
  `elements_registry.py:179`.

Resultado: `server/elements/personas/008-o-oxigeno.context.md` (9 líneas) está
commiteado, no lo lee nadie y nadie lo verifica. Plutonio es el caso limpio
opuesto (sin `engineBinding`, persona local compuesta y sí ejecutada); Yodo es el
otro extremo: `external_http_engine` **sin `personaId`**, así que og118 presenta
un nombre —"Yodo · Insult"— sin poder nombrar qué persona responde.

## Los dos ejes que el esquema confunde

La pregunta que originó esta tarjeta ("¿el prompt en el bot o en og118?") supone
un solo eje. Son dos, y son independientes:

| Eje | Pregunta | Dónde debe vivir |
|---|---|---|
| **Identidad** | ¿QUIÉN es el personaje? | `fi-personas`, un archivo, leído por TODA superficie que lo hable |
| **Contexto operativo** | ¿qué puede hacer AQUÍ? | la superficie: el bloque del elemento en og118, el suyo en discord-bot |
| **Ejecución** | ¿quién CORRE el turno? | `engineBinding` — y no dice nada sobre quién es dueño del prompt |

`engineBinding` hoy se lee como si contestara las tres.

## Qué hacer, en orden

1. **Que el esquema rechace la contradicción.** Un elemento con
   `engineBinding.is_external` **no puede** traer `personaCorePath` ni
   `personaPromptPath` — error al cargar, no archivo muerto. Es independiente de
   la dirección que se elija después, y habría cachado a Oxígeno el día que se
   escribió.
2. **Resolver Oxígeno**, que es decisión de Bernard: o se le quita el
   `engineBinding` y lo corre og118 con su persona compuesta, o se le borran los
   dos archivos locales y el personaje vive sólo en el motor remoto.
3. **Hacer real PERSONA-SSOT-1**: que discord-bot lea `vultur.core.md` de
   `fi-personas` y conserve sus 87 líneas propias como su bloque de contexto
   operativo, spliceadas en el marcador. Es trabajo en repo hermano
   ([[backlog-cross-repo-closure]]) y hay que verificar allá antes de empezar.

## La decisión que es del dueño

El paso 2. Y si Vultur en Discord y Vultur en og118 deben ser **el mismo**
personaje o dos con la misma raíz — porque las 87 líneas de diferencia pueden ser
drift accidental o pueden ser el contexto de Discord, y sólo Bernard sabe cuál.

Ver [[og118-elementos-118-gpt-personas]], [[prompts-as-content-not-code]] (el
prompt es contenido, y un contenido duplicado tiene el mismo olor que un
constante inline), [[00-constitution]] Art. 6 (una fuente de verdad por
superficie) y [[backlog-cross-repo-closure]].

## Cierre — 2026-09-10

Bernard, textual: *"mata vultur aquí, y todos los prompts de FI que den vida a
elementos, es el lugar incorrecto, deben estar en discord-bot y responder desde el
server como lo hace Yodo/Insult."*

**Los dos casos, resueltos en direcciones opuestas:**

- **Vultur** — la copia de og118 (`vultur.core.md`, 96 líneas) se borró. Nunca se
  ejecutó: Oxígeno es externo y `app.py` retornaba antes de componer el prompt. La
  viva sigue siendo `discord-bot/shared/personas/vultur.md`.
- **Reaper** — era el ÚNICO elemento local. Su personaje vivía partido en dos
  archivos de este repo; se empalmaron en el marcador y viajaron a
  `discord-bot/shared/personas/reaper.md` (commit `e7e196b`, v4.38.29). Plutonio
  pasó a `engineBinding: external_http_engine / personaId: reaper`.

**Verificado en vivo**, no por lectura: `POST /v1/turn` contra el persona-runner
real con `persona_id=reaper` contestó *"Reaper Arquetipo: analista implacable de
código, refactor brutal, ejecución sin titubeos"* — no la persona por default.

**El candado que se pedía en el paso 1 quedó mejor que un validador:** el campo ya
no existe. `personaCorePath`, `personaPromptPath`, `composed_persona()`,
`persona_path()`, `core_path()`, `FI_PERSONAS_DIR`, el marcador de empalme y los
kinds `local_runner_persona` / `shared_persona_prompt` se borraron. Un elemento
activo sin motor externo **no carga** — falla al arrancar en vez de contestar con
la persona base haciéndose pasar por Plutonio.

**El orden importó y se respetó:** el CD de discord-bot subió `reaper.md` ANTES de
que og118 tocara el registry. Al revés, Plutonio habría caído a la persona default
en silencio.

Coordinado con la sesión de discord-bot, que trabajaba lo mismo en paralelo: paró
sin commitear y su trabajo va doblado en este PR (el borrado de Vultur y la
doctrina invertida del README fueron suyos).
