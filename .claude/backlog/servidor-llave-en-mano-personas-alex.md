# Servidor llave en mano: tu propio Discord con bots hechos por nosotros

Status: Proposed
Proposed: 2026-08-15 por Bernard

## Qué es

Vender **el canary hecho producto**: un cliente tiene su propio server de Discord con sus
amigos, y bots con persona diseñada por Alex corriendo dentro. Tres patas:

| Pata | Qué se entrega | Dónde vive hoy |
|---|---|---|
| **Persona** | El bot no rompe personaje, y su política está escrita como criterio, no como lista | `shared/personas/*.md`, este repo |
| **Acceso medido** | Una llave AIRE capada y revocable por cliente; las transcripciones por llave son la evidencia | `aire-server`, `lending.py` + `tokens.py` |
| **Operación** | Que eso no se apague — la disciplina EC-GPS | el droplet, hoy a mano |

El motivo por el que Bernard lo levanta no es técnico: es **una fuente de ingresos propia
que lo saque del ciclo 1099/W2 a ser dueño de un negocio con revenue**.

### Por qué la persona es el activo, y no el gateway

El gateway es infraestructura: cualquiera lo rehace en una semana. Lo escaso es el criterio
clínico de Alex. La prueba está en su primera sesión (`training-contributors/sesion-01-alex-2026-08-10.md`):
Frugívoro —el bot vegano— recomendó **sal de gusano** (larva de maguey molida) porque su
prohibición en `shared/personas/frugivoro.md:143` es una **lista enumerada**, no un
razonamiento. La miel sí estaba en la lista; la intención ya era correcta; el criterio
"¿está en mi lista?" la dejó pasar igual. De ahí salió el issue #38: que deduzca
(de dónde sale → cómo se hace → ¿hay un ser sintiente? → fuera).

**Ese defecto lo tiene toda persona con política**: el bot de compliance, el de voz de
marca, el que no debe dar consejo médico. Todos están escritos como listas y todos se caen
con lo que nadie enumeró. Encontrarlo pide criterio sobre cómo la gente rodea una regla —
no un eval automático.

## El pleito: la pata de operación no escala, y es la que Bernard ofreció

```
  LO QUE VENDES              QUIÉN LO SOSTIENE         TECHO REAL
  ───────────────            ─────────────────         ──────────
  persona (Alex)      ──►    se escribe UNA vez   ──►  ∞ copias
  llave capada (AIRE) ──►    código, ya existe    ──►  ∞ clientes
  operación 24/7      ──►    BERNARD              ──►  2-3, y cayéndose
                              └─ 1 persona
                                 2 chambas encima
                                 0 h de holgura
```

Tres capas, y la tercera es la que muerde:

1. **Una persona y una llave se copian a costo cero. Una guardia no.**
2. **La asimetría del contrato invierte el 1099 en la dirección equivocada.** Hoy vende
   **horas acotadas** a $35 USD. Un servidor administrado vende **disponibilidad ilimitada
   a precio fijo**: mismo dueño de su tiempo, sin tope de horas y sin overtime.
3. **Deshace la evolución que ya hizo.** `aire-server/server/docs/genesis.md:65` lo dice: la
   magia de EC-GPS está *soldada a un cuerpo mortal* — muere el droplet, muere `gps_logs`,
   muere el negocio. AIRE le arrancó el cuerpo espejando el estado a Postgres.

```
      EC-GPS (el plano)                  AIRE (lo que ya existe)
   ┌─────────────────────┐            ┌─────────────────────┐
   │ droplet             │            │ droplet             │
   │  ├ demonio Perl     │            │  ├ demonio AIRE     │
   │  └ gps_logs ◄─ DATO │            │  └ (sin estado)     │
   └─────────────────────┘            └──────────┬──────────┘
             ✝                                   │ espeja
   muere el cuerpo → muere todo                  ▼
                                       ┌─────────────────────┐
                                       │ Postgres (Azure)    │
                                       │ transcripciones     │
                                       └─────────────────────┘
                                       muere el cuerpo → renace

          ── vender "MI droplet bien administrado" ──►  vuelve a soldar
             el valor al cuerpo, y encima el cuerpo es Bernard
```

Restricción medida, para que no se discuta con impresiones: el droplet es
`s-1vcpu-512mb-10gb` con **223 MB disponibles de 458, 1 core y el disco al 51%**
(`aire-server/.claude/backlog/32-the-nickname-door.md`). Eso se arregla con $24 al mes.
Lo que no se arregla con dinero es la guardia.

## La solución canónica a reusar (Art. 6)

Investigado el 2026-08-15 contra fuentes primarias. **La disciplina de Feria se queda como
ethos —cuerpo aburrido que no se apaga, SSH, cero sobre-ingeniería—; lo que se muda es
dónde vive el valor: al repo y al control plane.**

### 1. Ganado, no mascotas — el valor vive en git, no en el cuerpo

Un *pet* es el servidor configurado a mano cuyo conocimiento *"vive en la cabeza de una o
pocas personas, y ante un desastre restaurarlo toma días o semanas"*. Infra inmutable
invierte el despliegue: deja de ser *"actualizar código en un servidor"* y pasa a ser
*"reemplazar el servidor por una versión nueva"*, con código, config e infra versionados.

**Criterio de aceptación del producto:** si el droplet de un cliente muere, no se cura —
se vuelve a parir desde el repo, y el tiempo de ese renacimiento es un número medido, no
una esperanza.

Fuentes: [IOD](https://iamondemand.com/blog/devops-concepts-pets-vs-cattle/) ·
[Cloud Infrastructure Services](https://cloudinfrastructureservices.co.uk/vm-types-for-devops-pets-vs-cattle-vs-immutable/) ·
[Copado](https://www.copado.com/resources/blog/pets-vs-cattle-more-than-an-analogy-for-modern-infrastructures) ·
[DoHost](https://dohost.us/index.php/2026/04/22/pets-vs-cattle-transitioning-to-an-immutable-infrastructure/)

### 2. SLO + presupuesto de error — nunca se vende el 100%

Google SRE: *"100% probablemente nunca es el objetivo correcto de fiabilidad: no solo es
imposible de alcanzar, es típicamente más fiabilidad de la que los usuarios quieren o
notan"*. Se vende un número explícito (99.5% mensual ≈ **3.6 h** de caída permitida) y el
presupuesto es lo que **cierra la discusión con el cliente**, en vez de cerrarla la culpa
del operador. La política se escribe **antes**, dice qué pasa cuando el presupuesto se
agota, y nombra un árbitro.

Fuentes: [SRE Book — Embracing Risk](https://sre.google/sre-book/embracing-risk/) ·
[Error Budget Policy](https://sre.google/workbook/error-budget-policy/) ·
[Google Cloud](https://cloud.google.com/blog/products/management-tools/sre-error-budgets-and-maintenance-windows) ·
[GitLab](https://handbook.gitlab.com/handbook/engineering/error-budgets/)

### 3. El soporte es una decisión de producto, no un nivel de esfuerzo

El error nombrado es exactamente el de este item: *"muchos fundadores primerizos se
comprometen implícitamente a tiempos de respuesta de guante blanco en productos self-serve,
y colapsan cuando sube el volumen"*. La receta: primera respuesta a **24 h** (no 1 h), dos
bloques agendados al día (20 min + 10 min) en vez de bandeja reactiva, y monitoreo que
avise **antes que el cliente**. Cifra dura: **20-30% del tiempo** se va en mantenimiento
una vez vivo; se contrata ayuda a los **$10-15k USD de MRR**.

Fuentes: [Building It](https://building.it.com/articles/small-teams-support-without-burnout) ·
[Deelo](https://www.deelo.ai/blog/saas-customer-support-solo-founder) ·
[Two Cents](https://www.twocents.software/blog/solopreneur-saas-realistic-expectations-for-one-person-ops)

### 4. Control plane — para que N clientes no sean N mascotas

AWS: *"soportar muchos despliegues en entornos de cliente exige automatización que extienda
el aprovisionamiento y el monitoreo dentro de cada entorno, manejada desde un solo control
plane"*. La advertencia complementaria de Clerk es el techo de este producto: en
single-tenant *"las actualizaciones se aplican a cada instancia individualmente"* — si eso
es manual, el trabajo crece **lineal** con los clientes.

Fuentes: [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/manage-tenants-across-multiple-saas-products-on-a-single-control-plane.html) ·
[Clerk](https://clerk.com/blog/multi-tenant-vs-single-tenant) ·
[Red Hat](https://developers.redhat.com/articles/2022/05/09/approaches-implementing-multi-tenancy-saas-applications)

### Lo que la investigación NO contestó

Ninguna fuente da un **tope de clientes** ni una **estructura de precio ligada a la carga
de soporte** — la fuente de solopreneurs lo admite explícitamente. Ese número sale de medir,
no de copiar. No se inventa aquí.

## Lo que ya existe y no hay que reconstruir (Art. 6)

| Pieza | Estado verificado |
|---|---|
| Metering en dólares por llave, con corte | **Vivo**: `402 token_budget_spent` medido desde fuera del droplet, y `401` tras revocar |
| Préstamo de credencial a llave invitada | **Vivo**: `lending.py`, gateway `/v1/*`, verificado en cliente real |
| Pass-through sin costo | **Vivo** y fijado con test: quien trae su propia credencial se relaya intacto |
| Estado fuera del cuerpo | **Vivo**: transcripciones espejadas a Postgres |
| Personas con corpus RAG | **Vivo**: namespace de corpus + ingesta (ver `frugivoro-persona.md`) |

**La pieza chica que falta para que el producto exista:** hoy el metering **solo muerde a
las llaves invitadas**; el pass-through no se tarifica. Medir y capar también al que trae
su propia credencial es lo que convierte a AIRE de puerta en producto — y habilita el
modelo sin costo de mercancía (el cliente pone su propia llave de Anthropic).

## Bloqueadores que no se arreglan con código

1. **La credencial.** El cerebro corre hoy sobre la suscripción Claude Max que paga su
   empleador. El backlog de AIRE ya lo dice: *"serving third parties from a personal
   subscription is plausibly outside Anthropic's consumer terms"*. El slot limpio existe y
   está vacío: `AIRE_LEND_API_KEY`.
2. **México no califica** para Premium Apps ni Server Subscriptions de Discord — el cobro
   va por riel propio, por fuera, que la Developer Policy sí permite.
3. **El overlay de usuario vulnerable** (score clínico + líneas de crisis mexicanas en
   `khimeras_shared/guidance.py`) es una superficie de responsabilidad distinta cuando el
   server ya no es de cinco conocidos.
4. **Capacidad de Alex:** 3 h/semana, piloto hasta ~11-nov-2026.

## La decisión que es del dueño

- **El tope de clientes**, que es el número que ninguna fuente da y que define si esto es
  un negocio o una segunda chamba. Se mide, no se estima.
- **Qué SLO se vende** (99.5% mensual ≈ 3.6 h, o más flojo) y en qué horario hay soporte.
- **Si el cliente trae su propia llave de Anthropic** (sin costo de mercancía, sin problema
  de términos) o si Bernard revende tokens con margen.
- **Si el overlay clínico entra o no** en el producto vendido a desconocidos.

## Status / siguiente paso

Nada construido. Lo que desbloquea, en orden:

1. Acuñar la llave medida y poblar `AIRE_LEND_API_KEY` — apaga el bloqueador #1 **aunque
   nunca se cobre**, porque hoy se sirve a terceros desde la suscripción del empleador.
2. Escribir el hallazgo de la sal de gusano como pieza pública: el defecto, el experimento
   con control y el fix. Es la demo que vende sin necesitar todavía un cliente.
3. Medir el tiempo de renacimiento del droplet desde el repo. Ese número es la diferencia
   entre vender ganado y vender una mascota.

Ver [`persona-acompanamiento-issues-alex.md`](persona-acompanamiento-issues-alex.md),
[`frugivoro-persona.md`](frugivoro-persona.md) y, en `aire-server`, el item 32
(la puerta del nickname) y su slice (e).
