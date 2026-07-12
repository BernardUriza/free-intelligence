# AIRE

**A**rtificial **I**ntelligence **R**eflector **E**nvelope

> Tu agente se olvida de todo cuando se muere el contenedor. AIRE no.

Un servidor HTTP que envuelve el [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)
y **refleja** el transcript de cada sesión hacia **tu** base de datos. El contenedor
es desechable; la memoria es tuya y sobrevive.

```
POST /projects/avatar/messages
{ "prompt": "escribe el capítulo 2" }
```

Y el capítulo 2 se acuerda del capítulo 1 — aunque el contenedor que escribió el
capítulo 1 lleve tres días muerto.

## El nombre es la arquitectura

| | |
|---|---|
| **Reflector** | El SDK llama *mirror* a su gancho de persistencia: refleja el transcript a un store externo. AIRE es ese espejo, apuntando a tu Postgres. |
| **Envelope** | El sobre HTTP que contiene al agente. No lo importas: **le hablas**. |

## El hueco que llena

El `SessionStore` del Agent SDK es el gancho oficial para sacar la memoria del
disco y mandarla a una base de datos. **Nadie lo cablea.**

| | ¿Cablea `session_store`? | Dónde vive la memoria |
|---|---|---|
| [`claude-cookbooks/hosting`](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting) (oficial) | ❌ | dict en RAM + disco local |
| [Agno](https://github.com/agno-agi/agno) (41k ⭐) | ❌ | dict en RAM + disco local |
| **AIRE** | ✅ | **tu Postgres** |

Ambos pierden la sesión cuando muere el proceso. Verificado leyendo su código,
no su documentación.

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

## Estado

**Nada construido todavía.** Este repo empieza con el entendimiento, no con el código.
Lo que falta está en [`.claude/backlog/`](.claude/backlog/).

## Licencia

Por definir.
