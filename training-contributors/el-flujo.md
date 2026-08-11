# El flujo de una sesión

Protocolo repetible. Los tiempos son los reales de la sesión 1.

## Antes de la sesión

**1. Escoge el issue** siguiendo [`como-escribir-el-primer-issue.md`](como-escribir-el-primer-issue.md).
Esto es lo que hay que hacer bien; lo demás es logística.

**2. Consigue dos datos de la persona:**
- Su usuario de **GitHub** (para el invite al repo privado)
- Su ID de **AnyDesk** (10 dígitos) si el setup va a ser remoto

**3. Decide con qué cuenta va a entrar Claude Code en su máquina.**
Es lo único que puede detener la sesión en seco, y no se resuelve improvisando.

**4. Manda el invite y verifica la cuenta antes de invitar:**

```bash
gh api users/<usuario> --jq '{login, name}'          # que exista y sea quien crees
gh api -X PUT repos/<owner>/<repo>/collaborators/<usuario> -f permission=push
gh api repos/<owner>/<repo>/invitations --jq '.[] | "\(.invitee.login) — \(.permissions)"'
```

## Durante la sesión

### Fase 1 — Setup (operador, ~15 min)

Ver [`setup-maquina.md`](setup-maquina.md). Resumen: casi seguro ya tiene más
instalado de lo que crees. **Verifica antes de instalar**, y no le pongas el
entorno pesado.

Si es por AnyDesk, avísale antes de mover el mouse:

> "no le muevas 5 minutos, vas a ver el mouse moverse solo, soy yo"

### Fase 2 — La primera victoria (2 min)

Correr los tests **antes de tocar nada** y verlos verdes. Esto no es un trámite:
es el momento en que la persona ve que el repo funciona en su máquina y que
existe un botón que le dice "vas bien".

### Fase 3 — Devolver el control (1 min)

En cuanto Claude Code esté corriendo y logueado, **la máquina vuelve a ser suya**.
En AnyDesk: `Permissions → Control remote device` OFF (verificable — la palomita
del menú desaparece). Nunca uses "Block remote input": eso bloquea a la persona,
que es lo contrario.

De aquí en adelante las instrucciones van por **Discord**, no por el teclado.

**Y ahí se acaban los comandos del operador — todos, no solo los del trabajo.**
El setup termina cuando los comandos que ya corriste funcionaron; lo que sigue
es abrir Claude Code y devolver el teclado. Un `git pull`, una limpieza de rama,
un `--version` después de ese punto **también** son de la persona: se convierten
en un prompt que elle le manda a su Claude Code. AnyDesk se queda solo para
mirar.

Los prompts los redacta el operador **en Discord** y los manda la persona. No es
burocracia: en `#general` está Insult, así que cada prompt que pasa por ahí lo ve
el bot y puede sugerir e irse enterando de cómo va la sesión. Un comando tecleado
por AnyDesk es invisible para todos menos para quien lo tecleó.

### Fase 4 — El trabajo (el resto de la sesión)

El primer prompt lo escribe la persona con sus manos:

> `preséntate en español sencillo, dime en 5 líneas qué hace este proyecto, y luego léeme el issue #N y explícame el plan antes de tocar código`

De ahí en adelante ella dirige. El operador manda instrucciones por Discord y
observa; **no toca**.

Un detalle chico que vale mucho: enséñale el **texto fantasma** que Claude Code
pone en el prompt sugiriendo el siguiente paso, y que con **Tab** se rellena
solo. Quita la parálisis de "¿y ahora qué escribo?".

### Fase 5 — Review (operador)

Cuando abra el PR:

```bash
gh pr checks <n>
gh pr diff <n>
git worktree add --detach /tmp/review origin/<rama>   # correr las pruebas TÚ,
# ... correr los tests ...                            # no confiar solo en el CI
git worktree remove --force /tmp/review
gh pr review <n> --comment --body-file <archivo>
```

**El review abre con lo que hizo bien, y es específico.** "Está bien" no enseña
nada; "no hardcodeaste los alias, los leíste del registry, y eso evita un verde
falso" sí. Después, el bloqueador, y explicando por qué es un problema — no solo
qué cambiar.

### Fase 6 — El cierre

Merge, deploy, y **el último paso es de la persona**: que sea ella quien ejecute
la prueba real en la superficie real y vea su cambio funcionando.

Ese momento es el que hace que haya sesión 2. No lo tomes tú.

## Después

- Deja el siguiente issue escrito **antes de que termine la sesión**, si se
  puede sacando de algo que haya salido ese mismo día.
- La tarea entre sesiones es **leer el issue, sin resolverlo**. Ver la nota de
  inmersión abajo.

## Dos cosas que aprendimos a la mala

**El número de versión choca en silencio.** Si el repo exige bump de versión y
hay varias sesiones trabajando a la vez, dos ramas pueden tomar el mismo número.
Git **no marca conflicto** (los dos lados escribieron el mismo texto), el CI
pasa, y quedan dos builds distintos con el mismo tag. Se detecta solo comparando
a mano contra `origin/main` antes de mergear.

**Un verde puede mentir por el contexto, no por el código.** En la sesión 1, la
primera prueba de que el alias funcionaba estaba contaminada: el host tiene una
regla de continuación (`HOST_OWNS_RECEPTION=true`) por la cual el siguiente
mensaje va a quien venía en la conversación, aunque cambies de tema. Hubo que
montar un experimento con control — hablarle primero a otro bot para romper la
inercia — antes de poder afirmar que el cambio servía.

## La nota de inmersión

Vale la pena decirle explícitamente, desde el primer día:

> Aunque no le entiendas nada a lo que sale en la pantalla, léelo. Deja que las
> palabras te pasen por los ojos. Es una técnica real — inmersión / input
> comprensible — la misma con la que se aprende un idioma sin estudiar gramática:
> primero se exponen los ojos, el entender llega después. No tienes que entender
> hoy, nada más mirar.

Baja la ansiedad de no entender, que es lo que hace que la gente se salga.
