# AIRE

**A**rtificial **I**ntelligence **R**eflector **E**nvelope

> Tu agente se olvida de todo cuando se muere el contenedor. AIRE no.

Un servidor HTTP que envuelve el [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)
y **refleja** el transcript de cada sesión hacia **tu** base de datos. El contenedor
es desechable; la memoria es tuya y sobrevive.

```http
POST /projects/avatar/sessions/manuscrito/messages
Authorization: Bearer <token>

{ "prompt": "escribe el capítulo 2" }
```

Te responde con un stream SSE, evento por evento. Y el capítulo 2 se acuerda del
capítulo 1 — aunque el contenedor que escribió el capítulo 1 lleve tres días muerto.

Desde un cron, desde TypeScript, desde un botón, desde tu teléfono. Nadie necesita
Python, ni saber que el SDK existe.

## El nombre es la arquitectura

| | |
|---|---|
| **Reflector** | El SDK llama *mirror* a su gancho de persistencia: refleja el transcript a un store externo. AIRE es ese espejo, apuntando a tu Postgres. |
| **Envelope** | El sobre HTTP que contiene al agente. No lo importas: **le hablas**. |

## El hueco que llena

El `SessionStore` del Agent SDK es el gancho oficial para sacar la memoria del disco y
mandarla a una base de datos. Y el SDK **nunca borra de tu store** — su docstring te
delega la limpieza por escrito:

> *"Retention is the adapter's responsibility — implement TTL, object-storage lifecycle
> policies, or scheduled cleanup according to your compliance requirements."*

O sea: hacen falta **dos** cosas. El **espejo** y la **escoba**. Nadie tiene las dos.

| | Refleja a una DB | Servidor HTTP reutilizable | Housekeeping |
|---|---|---|---|
| [`claude-cookbooks/hosting`](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting) (oficial) | ❌ dict en RAM + disco | ⚠️ un solo proyecto (`cwd="/app"`) | ❌ |
| [Agno](https://github.com/agno-agi/agno) (41k ⭐) | ❌ dict en RAM + disco | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ Postgres/SQLite | ❌ lib interna de su app | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

Verificado **leyendo su código**, no su documentación:

- El cookbook y Agno guardan el mapeo de sesión en un `dict` **en RAM** y el transcript en
  **disco local** → pierden la memoria cuando muere el contenedor.
- ArcReel **sí** cablea el `SessionStore` (`DbSessionStore`, SQLAlchemy) — pero es una
  librería interna de su producto, bajo **AGPL**, no un servicio al que le puedas hablar
  desde otros proyectos.
- **Ninguno de los tres barre.** Cero `ttl`, cero `retention`, cero `cleanup`, cero archivado.
  Acumulan para siempre.

AIRE es el espejo **y** la escoba, detrás de un HTTP que cualquiera puede llamar.

## Qué NO es

- **No es un runner de VMs.** El contenedor no guarda nada, así que no necesita sobrevivir.
- **No es una librería.** No se importa; se llama por HTTP desde cualquier lenguaje.
- **No reimplementa el SDK.** El agentic loop, las herramientas, los subagentes, los
  permisos y el sandbox ya son del SDK. AIRE es el pegamento que faltaba.

## Arquitectura

```
   tus proyectos                AIRE                    lo permanente
  ─────────────────      ──────────────────      ────────────────────────
   cualquier lenguaje  ──►  POST /messages
                            Claude Agent SDK   ──►  transcript  →  Postgres
                            (contenedor
                             desechable)       ──►  el trabajo  →  git
```

Tres cosas, y solo una es AIRE:

- **La memoria** — el transcript, en tu Postgres. *Es lo único irreemplazable:
  borra el contenedor y AIRE sigue vivo; borra la base y AIRE murió.*
- **La obra** — lo que el agente produce, en git. Separado a propósito.
- **El cuerpo** — el contenedor. Nace, trabaja, muere. No guarda nada porque no le toca.

## Es tu basura

El SDK nunca borra: **la memoria se acumula para siempre.** Eso no es un defecto — es lo
que hace que no pierdas contexto. Pero alguien tiene que barrer, y ese alguien eres tú
(el SDK lo dice explícitamente).

Y como la basura es **tuya**, y vive en **tu** base, se le puede hacer de todo:

- **Retención** — TTL por proyecto, archivar sesiones frías, purgar lo que no sirve.
- **Backups programados** — es Postgres. Es `pg_dump` y una cron.
- **Auditoría** — qué le pediste, qué hizo, cuánto costó. Es un `SELECT`.
- **Una página para verlo todo** — porque la tabla es tuya.

Nada de esto es posible cuando la memoria vive del lado del proveedor.

## Estado

**Nada construido todavía.** Este repo empieza con el entendimiento, no con el código.
Lo que falta está en [`.claude/backlog/`](.claude/backlog/).

## Licencia

Por definir.
