# training-contributors

Cómo se entrena a alguien para contribuir a este repo **sin que sepa programar**,
dirigiendo a Claude Code en vez de escribir el código a mano.

No es teoría. Todo lo de aquí salió de la sesión 1 con Alex (2026-08-10), y cada
número está verificado contra la máquina, el repo o el hilo de Discord.

## El flujo, en una línea

**Un issue bien escrito + Claude Code en su máquina + Discord como canal de
instrucciones = un PR verde en producción el primer día.**

## Los documentos

| Documento | Para qué |
|---|---|
| [`el-flujo.md`](el-flujo.md) | El protocolo repetible de una sesión, paso por paso |
| [`como-escribir-el-primer-issue.md`](como-escribir-el-primer-issue.md) | La pieza que más pesa. Un issue mal escogido mata la sesión aunque todo lo demás salga bien |
| [`setup-maquina.md`](setup-maquina.md) | Qué instalar de verdad (mucho menos de lo que parece) y qué NO instalar |
| [`sesion-01-alex-2026-08-10.md`](sesion-01-alex-2026-08-10.md) | La bitácora con recibos: qué pasó, con horas y evidencia |

## Las tres cosas que hay que entender antes de dar una clase

**1. El issue es el 80% del resultado.**
La sesión 1 casi arranca con el issue #35 (failover de OAuth). Era imposible de
verificar sin agotar a propósito una cuenta Max, y tocaba `session_pool` +
inyección de token + reciclado de sesiones vivas. Se cambió por el #36 —
una línea en el registry, verificable con `pytest` en su propia máquina y
observable en Discord al desplegar. Ese cambio de issue fue la diferencia entre
una sesión que termina en PR y una que termina en frustración.

**2. La primera victoria va ANTES de tocar código.**
Correr los tests y verlos en verde en su propia computadora, antes de cambiar
nada, es lo que le dice a la persona "esto funciona y yo puedo verlo". Todo lo
demás cuelga de ahí. Si la sesión se acaba, se corta donde sea — pero nunca
antes de esa primera pantalla verde.

**3. Quien maneja el teclado es quien aprende.**
El setup lo hace el operador (por AnyDesk o como sea). El trabajo lo maneja
la persona. En el minuto en que uno toma el teclado "para ir más rápido", deja
de ser un training y se vuelve una demostración.

## El objetivo real

Que después de tres o cuatro vueltas del mismo ritual, ya no haga falta el
ritual: se le pasa el issue y lo resuelve sole.

Ver también: la sesión 2 arranca del [issue #38](https://github.com/BernardUriza/discord-bot/issues/38),
que nació de un bug real que salió en la sesión 1.
