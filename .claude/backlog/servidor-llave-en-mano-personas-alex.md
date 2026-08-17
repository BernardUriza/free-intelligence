# Servidor llave en mano: tu propio Discord con bots hechos por nosotros

Status: **Congelado hasta el inicio de 2027** (candado puesto el 2026-08-17 por Bernard)
Proposed: 2026-08-15 por Bernard

🔒 **No se ejecuta nada de este item ante un tercero antes de 2027, y no se le vuelve a
proponer.** Congelado: abrir cuenta en el MoR, cobros de prueba, contactar prospectos,
publicar la oferta, cotizar. Permitido: documentar, investigar y construir los activos que
el producto va a necesitar igual (una persona del catálogo, una corrección de código, un
runbook). La frontera: **si un desconocido se enteraría, está congelado.** El criterio y el
motivo viven en `compras/.claude/rules/oportunidad-de-ingreso-se-pesa-contra-si-escala-sin-bernard.md`
§ *Una fecha de arranque puesta por Bernard es un CANDADO*. Sólo él mueve la fecha (Art. 7).

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

## La cuenta: qué cuesta Alex, qué produjo, y a cuánto tiene que venderse el servidor

Ésta es la pregunta que originó el item (Bernard, 2026-08-17): *"cómo calcular cuál es el
valor de lo que está haciendo Alex realmente. Ahorita puede que esté muy inflado, y justo
por eso tenemos que tener un ROI en mente"*. El detalle de horas y pagos vive en su SSOT,
`compras/nomina-alex-khimeras.md` — aquí solo va la aritmética del producto.

### Lo que se pagó y lo que se entregó (verificado en git, no en el documento)

| | |
|---|---|
| Pagado hasta hoy | **1 pago · 120 USD · $2,042 MXN** (S1, 14-ago-2026) |
| Sesiones en S1 | 5 · **15 h acordadas · 11.75 h efectivas** (semana de arranque, atípica) |
| Entregado y **desplegado** | PR **#37** `40a4fea` (alias `fruggy`, v4.32.45) y PR **#39** `2c52a89`/`4ed8825` (Frugívoro vegano por deducción, v4.32.47) — los dos con autor `ferux485` en el historial |
| Entregado y **NO desplegado** | el ADN de **Valentis** (marco PAP/Hobfoll/Slaikeu, lente neuroafirmativa, escenarios y diálogos). `shared/personas/` tiene alice, frugivoro, insult y unborn_being — **valentis.md no existe en disco** |

### ¿Está inflado? Las dos lecturas son ciertas y dicen lo contrario

| Medida | USD/h | Contra la tarifa de Bernard ($35/h) |
|---|---:|---|
| El **contrato**: 120 USD ÷ 3 h base | **$40.00** | **14% MÁS CARO** que lo que él cobra |
| La **entrega real de S1**: 120 USD ÷ 11.75 h efectivas | **$10.21** | 71% más barato |

Al contrato está caro; a la entrega está regalado. **La respuesta honesta a "¿está
inflado?" es: hoy no, y el riesgo va en la dirección contraria a la que se teme** — el
precio es fijo y la entrega va a normalizarse hacia abajo, a las 3 h que el acuerdo
pactó. En régimen de 3 h reales el costo por hora se cuadruplica sin que nadie cambie
nada. Eso no es un argumento para pagarle menos: es la razón por la que el ROI no puede
medirse en horas.

### El piso de precio lo fija el TECHO DE OPERACIÓN, no el mercado

Costo mensual atribuible al producto:

| Renglón | USD/mes |
|---|---:|
| Alex, base 3 h | 519.60 |
| Droplet de AIRE | 4.00 |
| `insult-rg` en Azure (los bots) | 173.36 |
| **Subtotal en efectivo** | **696.96** |
| Tiempo de operación de Bernard (4 h/sem × $35, dentro del 20-30% que la investigación mide) | 606.20 |
| **Total con su tiempo valuado** | **1,303.16** |

Y el techo de operación son **2-3 clientes** (§ el pleito). Divide:

```
                       cubre Alex+infra    cubre TAMBIEN su tiempo
   3 clientes    ──►      $232 /mes            $434 /mes     por cliente
   2 clientes    ──►      $348 /mes            $652 /mes     por cliente
```

**Ese es el hallazgo:** casi todos ponen precio y luego se preguntan cuántos clientes
necesitan. Aquí es al revés — el techo de clientes está fijo de antemano, así que el
techo fija el piso: **~$250 USD/mes para no perder dinero, ~$435 USD/mes para que Bernard
no trabaje gratis.**

⚠️ **Los dos números son el punto de equilibrio ANTES de la comisión del riel de cobro, y
por eso no son el precio de lista.** El precio de lista es **$650 USD/mes**, y por qué
está en la subsección de abajo. A ese precio (~$11,000 MXN) el cliente **no es un cuate
con su Discord**: es una organización con presupuesto — una clínica, una escuela, una
colectiva, un despacho.

Si Alex sube a 6 h el subtotal en efectivo pasa a $1,216 y el equilibrio a **~$620
USD/mes** por cliente a 3 clientes — o sea el precio de lista de $650 deja de tener
holgura. La escala de sus horas mueve el precio del producto; no es una decisión de
nómina aislada.

### El precio de lista es $650 USD/mes, porque el equilibrio no paga la comisión

El equilibrio de arriba supone que el cliente paga $X y entran $X. No entran: el riel de
cobro (Merchant of Record, abajo) se queda con **5% + $0.50** por transacción. Con un
precio de $600 el neto es $569.50 y la ganancia por hora de Alex cae a **$31.18** —
debajo de los $35/h que Bernard cobra por su propio tiempo, o sea el producto pagaría
peor que la chamba que pretende sustituir.

Corrida a $650:

| A $650/mes | |
|---|---:|
| Neto por cliente (después de 5% + $0.50) | $617.00 |
| × 3 clientes | $1,851.00 |
| − costo mensual (Alex $520 + infra $177 + 4 h/sem de Bernard a $35) | −$1,303.16 |
| **Ganancia** | **$547.84 /mes** |
| Por hora de Alex (13 h/mes) | **$42.14** |

Y sigue siendo barato del lado del cliente: los tres juntos pagan **$23,400/año**, todavía
debajo del piso de una sola agencia.

### El mercado está partido en dos, y este precio cae en el hueco

Investigado el 2026-08-17. Las fuentes se contradicen por **tres órdenes de magnitud**, y
no es contradicción: son dos mercados distintos con el mismo nombre.

| Marco de comparación | Precio observado | $650/mes se lee como |
|---|---|---|
| SaaS de bot de estante (PeakBot, CommunityOne) | **$8.25–$14.99 /mes** | absurdo: 40× una suscripción |
| Retainer de mantenimiento de bot | **$70–$150 /mes** | caro sin explicación |
| Agencia, por proyecto | **desde $15,000 y hasta $50,000+** | la opción barata: $7,800/año es la MITAD del piso de una agencia |

**El marco de comparación decide el precio, no el producto.** Vendido como "suscripción de
bot" $650 es indefendible; vendido como **retainer administrado con diseño de persona
hecho por psicóloga** es la alternativa económica frente a un proyecto de agencia. La
consecuencia operativa es de posicionamiento, no de aritmética: el material de venta tiene
que fijar el marco de agencia antes de decir el número.

Fuentes: [Fiverr — costos de desarrollador de bots de Discord](https://www.fiverr.com/resources/guides/costs/discord-bot-developer) ·
[TechRadar — pricing 2026](https://techradar.info/how-much-does-it-cost-to-make-a-discord-bot-the-2026-pricing-guide/) ·
[CommunityOne](https://communityone.io/pricing/) ·
[PeakBot](https://peakbot.pro/blog/ai-discord-bot-pricing-comparison-2026)

### El riel de cobro desde México a EUA/UE: Merchant of Record

Un **Merchant of Record** es el vendedor legal de la transacción: calcula el IVA según la
ubicación del cliente, lo cobra, lo declara y lo remite — **sin registro de IVA en la UE ni
alta en MOSS**. Costo:

| Proveedor | Comisión |
|---|---|
| Paddle · Lemon Squeezy · Fungies | **5% + $0.50** |
| Dodo Payments | **4% + $0.40** |

El desempate contra cobrar directo no es la comisión, es el cumplimiento: un contador
multi-jurisdicción cuesta **$3,000–$10,000 USD/año**, y el 5% sobre 3 clientes a $650 son
**~$1,170 USD/año**. Con tres clientes el MoR cuesta entre un tercio y un octavo de la
alternativa, y no consume horas de nadie.

Fuentes: [Fungies — guía MoR para SaaS](https://fungies.io/merchant-of-record-for-saas-guide-2026/) ·
[FintechSpecs — Stripe vs Paddle vs Lemon Squeezy vs Polar](https://fintechspecs.com/blog/stripe-vs-paddle-vs-lemon-squeezy-vs-polar-merchant-of-record-b2b-saas/) ·
[BuildMVPFast](https://www.buildmvpfast.com/blog/lemon-squeezy-vs-polar-paddle-merchant-of-record-2026) ·
[GlobalSolo](https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026)

### Precio regional: se vende en país rico, se abarata en LatAm

Tesis de Bernard del 2026-08-17, y la investigación la sostiene. El precio por paridad de
poder de compra (PPP) mide **20–70% más ventas** en regiones de bajo poder de compra, **18%
más crecimiento** y **25% más ingreso por cliente**. O sea el precio regional no es
caridad: es el mecanismo que hace que $650 sea vendible en EUA/UE sin cerrar el mercado
local.

- **El abuso por VPN se mata exigiendo método de pago o dirección de facturación local.**
  En B2B es trivial: una organización tiene domicilio fiscal, y el MoR ya pide los datos
  de facturación para calcular el IVA.
- **Se enmarca como *precio regional*, nunca como "descuento por ser pobre".** Es la misma
  disciplina de registro del resto del expediente: el hecho se dice completo, el empaque no
  insulta al cliente.

Fuentes: [Monetizely — legalidad y ética de la discriminación regional de precio](https://www.getmonetizely.com/articles/is-regional-price-discrimination-legal-and-ethical-in-saas) ·
[Fungies — PPP pricing](https://fungies.io/purchasing-power-parity-saas-pricing-2026/) ·
[Dodo Payments](https://dodopayments.com/blogs/purchasing-power-parity-pricing-saas) ·
[PriceParity](https://priceparity.net/)

### El tier gratis: qué es exactamente, y cuál es su riesgo real

Los free tiers en productos de IA son estructuralmente peligrosos, y hay cifras: márgenes
brutos de **45–53%** y muchos negativos; GitHub Copilot perdía **$20 USD por usuario al
mes** con *power users* que costaban $80 contra una suscripción de $10; Cursor gastó
**$650M** en API de Anthropic generando **$500M** de ingreso.

**Pero en este producto la arquitectura ya acotó el gratis en dinero.** Cada nickname
invitado nace con tope de **$1.00 USD** (`AIRE_INVITE_BUDGET_USD`,
`aire-server/server/aire/tokens.py:36`), y el corte está verificado mordiendo con un 402
real. A **$0.108–$0.116 por turno** medido en el droplet
(`aire-server/.claude/backlog/32-the-nickname-door.md:159,184`), $1 son **~9 turnos**: eso
es un demo, no un servicio.

**El riesgo real del gratis no es el dinero, es la cuota semanal compartida.** El item 32
de `aire-server` lo dice textual: *"an invited key burning the weekly pool starves the
engine"* — un usuario gratis puede dejar mudos a los propios bots, que es exactamente lo
que pasó el **7-ago-2026**, cuando el límite semanal los calló.

La frontera, escrita para que no se re-discuta:

| Escala del gratis | Qué necesita |
|---|---|
| **Demo (~9 turnos, $1)** | es gratis hoy, con la llave que ya hay; no necesita llave medida |
| **Servicio (uso sostenido)** | necesita dólares propios |

Ese segundo renglón es **el mismo disparador ya registrado en el bloqueador #1** (el primer
desconocido pidiendo acceso), no uno nuevo, y no reabre la decisión del 2026-08-17 de no
acuñar llave medida (Art. 7).

Fuentes: [CRV — economía de la inferencia LLM](https://www.crv.com/content/llm-inference) ·
[Causo — costos de token y márgenes](https://hub.causo.ai/guides/how-to-price-ai-product-token-costs-margins-2026) ·
[Jeff Brokaw — márgenes brutos de IA](https://jeffbrokaw.com/blog/ai-gross-margins/) ·
[Digital Applied — unit economics 2026](https://www.digitalapplied.com/blog/ai-unit-economics-pricing-margins-services-2026-framework)

### 🔑 La pregunta de ROI que sí decide: ¿su nómina es CAPEX o OPEX?

Mismo dinero, misma persona, dos negocios opuestos:

| | Qué pasa con su costo | Margen |
|---|---|---|
| **Persona a la medida por cliente** (OPEX de servicio) | escala **lineal** con los clientes | se aplana; es consultoría con otro nombre |
| **Catálogo de personas escrito una vez y vendido N veces** (CAPEX de producto) | **fijo**, se amortiza en cada cliente nuevo | crece con cada venta |

La aritmética a favor: Valentis costó ~3 sesiones ≈ 1 semana ≈ **120 USD** de su tiempo.
Vendido a 3 clientes a $650/mes ($617 netos) se paga **más de 15 veces el primer mes**. Un
catálogo de 4-5 personas es un activo de ~$600 USD de costo hundido que se cobra
indefinidamente.

**Por eso el indicador que hay que vigilar no son sus horas — es cuántas personas del
catálogo están DESPLEGADAS.** Hoy: 4 en disco, 1 en borrador sin aterrizar, y 3 de las 5
sesiones de S1 se fueron a la que no aterrizó. Esa relación —sesiones invertidas contra
personas desplegadas— es la métrica de ROI de esta nómina, y es la que hay que reportar
cada semana en lugar del conteo de horas.

## Bloqueadores que no se arreglan con código

1. **La credencial — 🔒 DECIDIDO el 2026-08-17 por Bernard, NO se re-propone (Art. 7).**
   El cerebro corre sobre la suscripción Claude Max que paga su empleador, y **así se
   queda**: `AIRE_LEND_OAUTH_TOKEN` sigue siendo el relleno correcto y **no se acuña
   llave medida**. El backlog de AIRE decía *"serving third parties from a personal
   subscription is plausibly outside Anthropic's consumer terms"* — pero hoy **no hay
   terceros**: cero usuarios que no sean Bernard, o sea uso propio, no reventa. El
   disparador que reabre el tema es **el primer desconocido pidiendo acceso por correo**,
   no la llegada de un cliente que pague. Registrado en `aire-server` items 32 y 34.
2. **México no califica** para Premium Apps ni Server Subscriptions de Discord — el cobro
   va por riel propio, por fuera, que la Developer Policy sí permite.
3. **El overlay de usuario vulnerable** (score clínico + líneas de crisis mexicanas en
   `khimeras_shared/guidance.py`) es una superficie de responsabilidad distinta cuando el
   server ya no es de cinco conocidos.
4. **Capacidad de Alex:** 3 h/semana, piloto hasta ~11-nov-2026.

## La decisión que es del dueño

- **El tope de clientes**, que es el número que ninguna fuente da y que define si esto es
  un negocio o una segunda chamba. Se mide, no se estima.
- **Confirmar el precio de lista en $650 USD/mes** (equilibrio $250/$435 antes de comisión;
  a $600 la hora de Alex cae a $31.18, debajo de los $35/h de Bernard).
- **Cuál MoR** se contrata: Paddle / Lemon Squeezy / Fungies a 5% + $0.50, o Dodo Payments
  a 4% + $0.40.
- **Qué se hace con LatAm:** gratis, o precio regional reducido con verificación por
  dirección de facturación local.
- **Qué SLO se vende** (99.5% mensual ≈ 3.6 h, o más flojo) y en qué horario hay soporte.
- **Si el cliente trae su propia llave de Anthropic** (sin costo de mercancía, sin problema
  de términos) o si Bernard revende tokens con margen.
- **Si el overlay clínico entra o no** en el producto vendido a desconocidos.

## Status / siguiente paso

Nada construido. Lo que desbloquea, en orden:

1. ~~Acuñar la llave medida y poblar `AIRE_LEND_API_KEY`~~ — **descartado el 2026-08-17
   por Bernard.** Sin usuarios ajenos no hay reventa que regularizar, y una llave medida
   es un costo sin nadie detrás. Se retoma solo con el disparador del bloqueador #1.
2. Escribir el hallazgo de la sal de gusano como pieza pública: el defecto, el experimento
   con control y el fix. Es la demo que vende sin necesitar todavía un cliente.
3. Medir el tiempo de renacimiento del droplet desde el repo. Ese número es la diferencia
   entre vender ganado y vender una mascota.
4. 🔒 **CONGELADO hasta 2027** — abrir cuenta en el MoR y probar un cobro de $1 USD para
   medir la comisión real. Es el primer paso que existe frente a un tercero, así que cae
   entero dentro del candado. No se propone antes de la fecha.

**Lo ejecutable mientras el candado esté puesto son los pasos 2 y 3**, que construyen
activos que el producto necesita de todos modos. El 1 está descartado y el 4 congelado.

El precio ya no está abierto: **$650 USD/mes**, con equilibrio en $250/$435 antes de
comisión, y el material de venta encuadrado contra agencia ($15,000–$50,000+ por proyecto),
nunca contra suscripción de bot ($8.25–$14.99/mes).

Ver [`persona-acompanamiento-issues-alex.md`](persona-acompanamiento-issues-alex.md),
[`frugivoro-persona.md`](frugivoro-persona.md) y, en `aire-server`, el item 32
(la puerta del nickname) y su slice (e).
