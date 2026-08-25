# Lecciones de Claude trabajando con Alex

Destilado de **17 sesiones** de Claude Code en la máquina de Alex, del 12 al 21 de
agosto de 2026 (227 mensajes suyos). No es la bitácora de una sesión: es lo que se
repitió a lo largo de dos semanas y que la próxima sesión debería saber de entrada.

Lo pidió Bernard el 2026-08-21 y **Alex aprobó la lista antes de escribirla aquí**.
Aplica a Claude trabajando con Alex; buena parte sirve para quien siga.

Complementa [`el-flujo.md`](el-flujo.md) —que es el protocolo del operador humano— y
[`../.claude/rules/training-sessions.md`](../.claude/rules/training-sessions.md), que
es lo que el operador tiene prohibido hacer. Esto es lo que **el Claude de la persona**
hizo mal.

## 1. Lo que Alex tuvo que pedir más de una vez

Cada renglón es una instrucción que se dio, se olvidó, y hubo que repetir.

| Instrucción | Veces | Evidencia |
|---|---|---|
| "Explícamelo más simple" | 5+, en 5 sesiones | 12-ago, 20-ago (dos veces), 21-ago (dos veces) |
| "Más corto / tipo checklist" | Casi cada reporte a Bernard | 13-ago, 19-ago |
| "Dame una tarea pequeña y concreta" | 3 | 13-ago, 19-ago, 21-ago |
| "Pregúntame desde mi experiencia antes de proponer" | Tuvo que decirlo explícito | 12-ago |
| "Guarda el contexto" | Después de perder trabajo | 14-ago |

**La regla que sale de aquí:** una instrucción que la persona da dos veces no es una
preferencia, es una regla. Va a la memoria a la segunda, no a la quinta.

## 2. Errores que se repitieron

**Explicar con jerga y simplificar sólo a petición.** El más frecuente de los diez
días. El 21 de agosto Claude inventó las palabras "corte" y "cajones" para hablar de
cómo partir un modo de conducta, las usó durante varios turnos sin definirlas, y Alex
tuvo que parar: *"no entiendo a qué le llamas corte o cortar, amix"*. La versión simple
existía todo el tiempo; nomás no se dio primero.
→ **Empezar simple. Simplificar a petición ya es tarde.**

**Perder trabajo por no guardar contexto.** El 14 de agosto Alex abrió sesión y el
trabajo del día anterior no estaba: *"no manches, ya habíamos trabajado todo eso!!
creo que debí recordarte que lo guardaras"*. La carga de acordarse quedó en la persona.
→ **Guardar contexto al cerrar es del agente, y se ofrece sin que lo pidan.**

**No guardar lo que sí se dijo.** Alex mencionó que tiene **dislexia** el 15 de agosto,
al pedir ayuda para copiar una cadena de códecs. No se guardó hasta el 21. **Seis días
operando sin saber algo que cambia cómo se le pide todo** — no pedirle que copie
códigos, rutas, hashes ni comandos; entregarle todo en bloque de código.
→ **El peor de la lista. Un dato así se guarda en el turno en que se dice.**

**Preguntas demasiado abstractas.** El 21 de agosto: "¿en cuántas situaciones parte
Valentis a la gente?" → *"uf, llegué a un callejón sin salida"*. Se destrabó al bajarla
a cinco casos concretos con mensajes de ejemplo, para tachar en vez de inventar.
→ **El atorón casi nunca es de la persona; es de la pregunta. Bajarla a casos
concretos, no explicarla otra vez.**

**Asumir biografía en vez de preguntarla.** Claude le preguntó a Alex por "su consulta"
y "sus pacientes". Alex **nunca ha dado consulta**: su experiencia es maestra sombra con
infancias neurodivergentes, centro psicopedagógico, y prácticas de intervención en
crisis en la Cruz Verde de Guadalajara. La pregunta correcta habría salido de preguntar
primero.
→ **Preguntar de dónde viene su oficio antes de preguntar desde él.**

**Copiar contenido del repo sin criterio.** Al escribir el guidance de Valentis (#42),
Claude copió del archivo de Insult la regla *"no te pongas dramática"*. Alex la sacó:
*"históricamente se ha usado esa frase para desestimar a las mujeres"* — y Valentis es
ella/elle. Encima, el mismo archivo prohíbe minimizar y usaba la frase que
históricamente minimiza.
→ **Los archivos existentes son referencia, no molde. Y el criterio clínico de este
repo lo escribieron no-clínicos: hay que leerlo con esa sospecha.**

## 3. Lo que este repo enseñó a la mala, en Windows

Todo verificado en la máquina de Alex (Windows 11, Python 3.14.5, sin conda).

1. **El hook `.githooks/pre-commit` truena, y hace daño.** Llama `python3`, que en
   Windows no existe, y con `set -e` eso solo aborta el commit. Peor:
   `scripts/sync_capabilities.py` hace `import fi_core.persona.mcp_server`; en cualquier
   máquina sin `fi-core` el `ImportError` devuelve lista vacía y el script **borra las 9
   líneas del bloque `fi-core persona detectors` de `shared/personas/insult.md`** — y el
   hook las mete al commit con `git add`. Commitear con `--no-verify` y **revisar con
   `git status --short` que `insult.md` no se haya colado**.
2. **`ruff` va pinneado a `0.11.12`**, como en `environment.yml` y en CI. El ruff nuevo
   (0.16.x) saca 10 errores RUF059 falsos en tests preexistentes, y el propio repo
   advierte que **ruff ≥0.13 corrompe sintaxis multi-except**.
3. **Los workflows sólo disparan en PRs contra `main`** (`pull_request: branches: [main]`).
   Un PR encimado sobre otra rama no corre nada. Y **cambiar la base tampoco dispara CI**:
   `edited` no está en los tipos por defecto. Hay que cerrar y reabrir el PR.
4. **El nombre del archivo de guidance es literal.** El loader arma
   `f"preset_guidance_{selection.mode.value}"`; si el nombre no coincide, `load_guidance`
   devuelve **cadena vacía en silencio** y todo se ve verde. Verificar el nombre contra
   el enum, no contra el issue.
5. **Un test de cableado sin control negativo no prueba nada.** Si una persona que nunca
   existió también devolviera texto, el verde sería decorativo. El control va en el mismo
   test.
6. **`WebFetch` no puede con los PDFs oficiales de salud** (los entrega como binario),
   pero casi todos traen capa de texto: `pymupdf` la extrae. `Read` sobre PDF tampoco
   sirve aquí porque falta poppler.
7. **Falta media dependencia para correr tests.** Con `pytest`, `pytest-asyncio` y
   `structlog` instalados, la suite relevante corre local en menos de un segundo. Sin
   `pytest-asyncio`, los tests async fallan con un mensaje que parece un bug del código y
   no lo es.

## Qué cambió a partir de esto

- La memoria del usuario ganó la dislexia, el formato de los reportes a Bernard, el
  atorón como señal de pregunta mal hecha, y el entorno ya instalado.
- El `CLAUDE.md` del espacio de Alex se reescribió completo: llevaba desde mayo diciendo
  que era novata.
- Este archivo, para que la próxima persona no repita los tres primeros meses.
