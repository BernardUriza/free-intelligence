# Capacitación — el operador no teclea, dicta prompts por Discord

Aplica a toda sesión de entrenamiento de un contribuidor (Alex y quien siga). El
protocolo humano completo vive en [`training-contributors/el-flujo.md`](../../training-contributors/el-flujo.md);
esto es lo que **Claude, como operador, tiene prohibido hacer**.

## La regla

**El operador ejecuta comandos SOLO durante la fase de setup, y para. En cuanto
los comandos de setup que corriste ya funcionaron, el siguiente paso es abrir
Claude Code en la máquina de la persona y devolver el teclado.** De ahí en
adelante:

- **AnyDesk pasa a SOLO LECTURA** (`Permissions → Control remote device` OFF).
  Sirve para *observar* — ver qué está pasando en su pantalla, leer la salida,
  detectar dónde se atoró. No para teclear.
- **Los prompts los escribe el operador en Discord; los manda la persona.** No
  se los tecleas tú en su terminal. Tú redactas el prompt en `#general`, elle lo
  copia a Claude Code y lo envía con sus manos.
- **Cero comandos "de operador" después del setup.** Ni un `git pull`, ni un
  `git branch -d`, ni un `--version`, ni "nomás este chiquito para ir más
  rápido". Si hace falta correrlo, se convierte en un prompt que la persona le
  manda a su Claude Code. Ese es el trabajo: aprender a dirigir al agente,
  incluido el mantenimiento aburrido.

## Por qué Discord y no la terminal

Porque `#general` no es un canal de chat cualquiera: **Insult está ahí**. Cada
prompt que pasa por Discord lo ve la persona, lo ve el operador y lo ve el bot —
así Insult se entera de cómo va la sesión, puede sugerir, corregir el rumbo y
acompañar. Un comando tecleado por AnyDesk es invisible para todos menos para el
que lo tecleó, y desperdicia al copiloto que ya está en la sala.

## El tell de que lo estás violando

Te descubres tecleando en la máquina de la persona **después** de que el setup
ya quedó, con la justificación de que es "rápido", "aburrido" o "es chamba de
operador". Esa es exactamente la frase que convierte un training en una
demostración ([`README.md`](../../training-contributors/README.md): *quien maneja
el teclado es quien aprende*).

## Por qué existe (2026-08-11, sesión 2 de Alex)

Terminado el setup —repo actualizado a v4.32.46, árbol limpio— seguí corriendo
comandos por AnyDesk: borrar la rama vieja, listar directorios, revisar
versiones. Bernard cortó el turno: *"si los que ya corriste ya te funcionaron,
lo siguiente es abrir Claude y pedirle a Alex que mande prompts… tú solo utilizas
AnyDesk como solo lectura y le escribes en Discord los prompts que debe mandar, y
así Insult puede dar sugerencias e irse enterando de cómo va, pero no quiero que
estés tú ejecutando comandos."*
