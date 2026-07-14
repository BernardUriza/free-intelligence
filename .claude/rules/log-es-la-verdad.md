# El log es la verdad, la vista es un caché (la ley de AIRE)

Regla del repo `aire-server`. Instancia la génesis y el respaldo científico del
`CLAUDE.md` (sección *"El mesero y la magia"*). Si vas a tocar la memoria o el
render de AIRE, esta ley manda.

## El teorema

El **transcript append-only** que el `session_store` refleja a Postgres es **LA
ÚNICA FUENTE DE VERDAD**. Todo lo demás —la vista SSR, el pool de clientes en RAM,
cualquier caché— es **derivado del log**, nunca al revés. Esto no es opinión de
diseño: es el consenso de la ingeniería de datos moderna.

- **Jay Kreps, «The Log»** (creador de Kafka): el log es la abstracción de
  almacenamiento más simple posible —append-only, totalmente ordenado— y **la
  tabla es un caché / vista derivada del log**.
  <https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying>
- **Pat Helland, «Immutability Changes Everything»** (ACM Queue / CIDR 2015):
  *"los contadores no usan borradores"*; **«el contenido de la base de datos es
  un caché de los últimos valores que están en los logs»**.
  <https://queue.acm.org/detail.cfm?id=2884038>
- **WAL / ARIES** (Postgres, Oracle, MySQL): la durabilidad se funda en un log
  append-only secuencial.
- **Martin Fowler, Event Sourcing**: el event store append-only es la única
  fuente de verdad; el estado es una vista derivada (ejemplo: el control de
  versiones). <https://martinfowler.com/articles/201701-event-driven.html>

## La génesis (por qué esta forma, y no otra)

AIRE es, pieza por pieza, la máquina de **EC-GPS** (Carlos Feria Tapia): receptores
GPS empujando por GPRS → un **daemon de Perl** escuchando en un puerto → escribe
`gps_logs` (append-only) → un **mesero PHP** que solo la lee y la muestra. AIRE es
lo mismo con el parser vuelto inteligencia:

- **El engine (`aire/engine.py`) es el daemon-que-escucha** — patrón Reactor / event
  loop (el problema C10K, 1999). El socket que escucha es eterno; lo único nuevo
  entre el `accept()` y el `INSERT` es que el parser ahora razona. **La IA es el
  *transform*, no el chasis.**
- **`gps_logs` = el `session_store`.** La tabla append-only en Postgres.
- **El mesero PHP = `render.py` / el SSR.** Lee el log y lo pinta. Reemplazable.

## Prohibiciones (lo que esta ley te impide hacer)

1. **NUNCA hagas que la vista o un caché sean la fuente de verdad.** El pool de
   `ClaudeSDKClient` en RAM es **caché caliente, no verdad**: un miss se reconstruye
   desde el store con `resume=`. Si el proceso muere, la verdad sigue en Postgres.
   *Matar el proceso → `GET` → repintar desde el store* debe funcionar siempre; si
   deja de funcionar, rompiste la ley.
2. **NUNCA muevas la memoria a un cuerpo mortal.** Ésa es la única evolución de AIRE
   sobre EC-GPS: la magia de Carlos FT está soldada a su droplet (si muere, muere
   `gps_logs`). La memoria de AIRE vive en la base del **dueño**, desacoplada del
   proceso que la escribe. Un transcript en el disco de la VM, en un checkpoint
   local, o en un dict que no se persiste, **le devuelve un cuerpo al agente** — y
   por la prueba de fuego del `CLAUDE.md`, eso es la muerte.
3. **El transcript es append-only; no lo mutes.** La retención (housekeeping) se
   hace con `DELETE ... WHERE mtime < cutoff` como política del adapter, nunca
   reescribiendo entradas. Corregir es agregar, no borrar (Helland).

Ver también el `CLAUDE.md` (secciones *"El espíritu"*, *"La génesis"*, *"El mesero
y la magia"*) y `aire/store.py` (el adaptador Postgres oficial, copiado).
