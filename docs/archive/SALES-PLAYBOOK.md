# Free Intelligence — Sales Playbook

**Versión**: 1.0
**Fecha**: Octubre 2025
**Propósito**: Guía completa de venta consultiva para FI-Cold
**Audiencia**: Vendedores fraccionarios + Bernard

---

## 🎯 Overview

Este playbook contiene todo lo necesario para vender FI-Cold a hospitales/clínicas en México:
- Pitch script de 10 minutos (intro calls)
- Discovery questions
- Handling objections
- Closing techniques
- Deal structure

**Filosofía de venta**: Consultiva, no transaccional. Entendemos su negocio ANTES de vender.

---

## 📞 Pitch Script (10 minutos)

### Estructura del Intro Call (30 min total)

```
0:00-0:05 (5 min)  - Rapport + Discovery
0:05-0:15 (10 min) - Pitch + Demo conceptual
0:15-0:25 (10 min) - Q&A + Objeciones
0:25-0:30 (5 min)  - Next steps + Closing
```

---

### Parte 1: Rapport + Discovery (5 min)

**Opening**:
```
"Hola [Nombre], gracias por el tiempo. Sé que tienes agenda apretada, así que vamos directo al grano.

Soy [Tu Nombre], trabajo con Free Intelligence. Desarrollamos un sistema de IA para consultas médicas que ayuda a hospitales como [Nombre Hospital] a reducir ~67% el tiempo que sus médicos gastan en documentación.

Antes de contarles cómo funciona, me gustaría hacerles 3 preguntas rápidas para entender su operación. ¿Les parece?"
```

**Discovery Questions** (3-5 min):

1. **Volumen**:
   > "¿Cuántas consultas procesan al día, aproximadamente?"

   *Buscar*: >50 consultas/día = buen fit. <20 = no prioritario.

2. **Dolor documentación**:
   > "¿Cuánto tiempo estiman que sus médicos gastan documentando cada consulta? ¿Intake + SOAP notes?"

   *Buscar*: Si dicen >10 min total = dolor fuerte. Si dicen "no es problema" = no es fit.

3. **Compliance/Auditorías**:
   > "¿Han tenido auditorías recientes? ¿NOM-004, certificaciones? ¿Cómo les fue?"

   *Buscar*: Si tuvieron problemas de documentación = pain point. Si todo perfecto = menos urgencia.

4. **IT Infrastructure**:
   > "¿Tienen un servidor o infraestructura IT local? ¿O todo es cloud?"

   *Buscar*: Si tienen LAN/servidor = fácil implementación. Si 100% cloud = educación necesaria.

5. **Decisión/Budget**:
   > "¿Quién más debería estar en esta conversación? ¿Director médico, IT, finanzas?"

   *Buscar*: Identificar stakeholders. Si dicen "yo decido solo" = más rápido.

**Transition al pitch**:
```
"Perfecto. Déjame compartirles cómo Free Intelligence Cold puede ayudarles específicamente con [su pain point mencionado]."
```

---

### Parte 2: Pitch (10 min)

#### Problema (1 min)

```
"En México, los médicos gastan ~40% de su tiempo en documentación, no en atender pacientes.

Esto genera:
• Burnout médico (principal causa de renuncia)
• Menos pacientes atendidos (pérdida de ingreso)
• Errores de documentación (riesgo en auditorías)
• Costo alto de contratar más médicos ($600k-$1M MXN/año por médico)

[Nombre Hospital] procesa [X] consultas/día. Si cada médico gasta 10 min documentando, son [X*10/60] horas/día perdidas. Eso es casi [X/5] consultas más que PODRÍAN atender si documentaran más rápido.
```

#### Solución (3 min)

```
"Free Intelligence Cold es un sistema de consultas asistidas por IA que hace 3 cosas:

1️⃣ **IntakeCoach** (2 min vs 8 min)
   - Asistente conversacional que recopila información del paciente
   - Detecta urgencia automáticamente (LOW/MODERATE/HIGH/CRITICAL)
   - Ejemplo: Paciente dice 'dolor de pecho', sistema pregunta irradiación, intensidad, factores de riesgo
   - Si detecta patrón crítico (widow maker), alerta inmediata

2️⃣ **Generación SOAP automática** (30 segundos vs 5 min)
   - Genera nota SOAP completa (Subjetivo, Objetivo, Assessment, Plan)
   - NOM-004-SSA3-2012 compliant (formato estándar de México)
   - Médico valida, ajusta si necesario, y confirma
   - No reemplaza al médico, lo ASISTE

3️⃣ **Audit trail completo** (para compliance)
   - SHA256 hash de cada interacción (non-repudiation)
   - Export de evidencia para auditorías
   - Append-only (datos nunca se borran, solo se agregan)
   - HIPAA-style audit logs
```

#### Diferenciadores (2 min)

```
"Lo que nos hace únicos:

✅ **100% local** (datos NUNCA salen de su red)
   - Opera en su servidor o laptop dedicada
   - Sin dependencia de internet (funciona offline)
   - Sus datos = su propiedad, siempre

✅ **Sin PHI persistente en piloto**
   - Piloto de 60 días usa datos demo/anonimizados
   - Cero riesgo de compliance durante testing
   - Si funciona, migramos a producción con PHI

✅ **Piloto SIN COSTO**
   - 60 días gratis (hardware + software + soporte)
   - Ustedes solo proporcionan: espacio + 2-4 médicos que lo usen
   - Si no les gusta, retiramos equipo y fin

✅ **ROI claro**
   - +40 pacientes/día sin contratar más médicos
   - O liberar 2-3 horas/día por médico
   - ROI típico: 8-10 meses
```

#### Resultados esperados (2 min)

```
"¿Qué pueden esperar en el piloto de 60 días?

📊 **Métricas técnicas**:
- Uptime >95% (sistema disponible siempre)
- Response time <3 segundos (no ralentiza consulta)
- ≥30 notas SOAP generadas (uso real)

🩺 **Métricas clínicas**:
- 30-40% reducción en tiempo de intake
- 50-70% reducción en tiempo de documentación
- 90%+ accuracy en triage de urgencia
- 100% compliance NOM-004

👥 **Métricas de satisfacción**:
- ≥4/5 satisfacción de médicos (encuesta semanal)
- ≥80% adopción de staff (todos lo usan)
- <5 reportes de bugs críticos

Si cumplen estas métricas, consideramos el piloto exitoso y pasamos a producción.
```

#### Pricing (2 min)

```
"Para producción (post-piloto), tienen 2 opciones:

**Opción A: Compra**
- Hardware: $85,000 MXN (DELL Latitude i7, 32GB RAM, 1TB SSD)
- Software (licencia perpetua): $120,000 MXN
- Implementación: $40,000 MXN (on-site, capacitación, soporte)
- **Total: $245,000 MXN** (pago único)
- Soporte anual: $24,000 MXN (10% licencia)

**Opción B: Leasing (36 meses)**
- $2,900 MXN/mes (todo incluido: hardware + software + soporte)
- Sin costo inicial
- Después de 36 meses, ownership transferido

**ROI**:
- Si atienden +40 pacientes/mes a $500 c/u = +$20,000 MXN/mes
- O si ahorran 2h/día/médico × 20 días × 3 médicos = 120h/mes
- 120h × $500/h = $60,000 MXN valor tiempo ahorrado
- Leasing se paga solo en <1 mes, compra en ~4 meses

**Primeros 5 pilotos**: 20% descuento + upgrade de hardware gratis.
```

---

### Parte 3: Q&A + Objeciones (10 min)

**Transition**:
```
"Eso es Free Intelligence Cold en resumen. ¿Qué preguntas tienen?"
```

*[Ver sección Handling Objections abajo para respuestas detalladas]*

---

### Parte 4: Next Steps + Closing (5 min)

**Si interesados (strong buy signals)**:
```
"Me da gusto que les interese. Los siguientes pasos son:

1️⃣ **Hoy**: Les envío por email:
   - One-pager de 1 página (resumen de todo esto)
   - Video demo de 90 segundos
   - LOI template (Letter of Intent para piloto 60 días)

2️⃣ **Esta semana**: Ustedes:
   - Revisan documentos
   - Consultan con IT/Legal si necesario
   - Identifican 2-4 médicos para el piloto

3️⃣ **Próxima semana**: Coordinamos:
   - Demo en vivo de 30 min (presencial u online)
   - Revisión de requisitos técnicos con IT
   - Firma de LOI (si todo bien)

4️⃣ **Semana 3**: Implementación:
   - Día 1: Instalación on-site (4-6 horas)
   - Día 1: Capacitación (4 horas)
   - Día 2-60: Piloto activo, soporte remoto

¿Les parece bien este timeline? ¿O necesitan más tiempo para decisión interna?"
```

**Si necesitan pensarlo (warm leads)**:
```
"Totalmente entendible. Esta es una decisión importante.

¿Qué les ayudaría a tomar la decisión?
- ¿Necesitan demo en vivo primero?
- ¿Necesitan consultar con alguien más? (IT, Legal, Dirección)
- ¿Tienen objeciones específicas que podamos resolver?

Propongo: Les envío el one-pager y video, ustedes lo revisan internamente, y nos reconectamos en [X días]. ¿Les parece?"
```

**Si no interesados (lost opportunity)**:
```
"Entiendo. ¿Me pueden compartir cuál es la razón principal?
[Escuchar]

¿Sería mejor timing en 6 meses? ¿O definitivamente no es un fit?

[Si es timing]: "Sin problema. Los mantengo en radar para [mes]. ¿Les puedo enviar el one-pager de todas formas para que lo tengan?"

[Si es no-fit]: "Entendido. Gracias por el tiempo. Si conocen a alguien en otro hospital que sí tenga este pain point, les agradecería el referral."
```

---

## 🔍 Discovery Framework (BANT + CHAMP)

### BANT (Clásico)

- **Budget**: ¿Tienen presupuesto IT para 2025/2026? ¿Rango?
- **Authority**: ¿Quién toma la decisión final? ¿Necesitan aprobación de otros?
- **Need**: ¿Documentación es problema reconocido? ¿Qué intentaron antes?
- **Timeline**: ¿Cuándo necesitan solución? ¿Hay deadline (auditoría, certificación)?

### CHAMP (Consultivo)

- **CHallenges**: ¿Cuál es su reto #1 operativamente?
- **Authority**: ¿Quién más está involucrado en esta decisión?
- **Money**: ¿Qué inversión es razonable para resolver este problema?
- **Prioritization**: ¿Esto es top 3 prioridades para este año?

**Red flags** (descalificar lead):
- Volumen <20 consultas/día (muy pequeño)
- "No tenemos problema de documentación" (no hay dolor)
- "Necesito consultar con 10 personas" + no tiene influencia (blocker)
- Presupuesto $0 + no quieren leasing (no pueden pagar)

**Green flags** (prioritizar):
- Volumen >100 consultas/día (alto impacto)
- "Médicos se quejan todo el tiempo de documentación" (dolor fuerte)
- "Yo decido, solo consulto con IT" (corto ciclo)
- "¿Cuándo podemos empezar?" (alta urgencia)

---

## 🛡️ Handling Objections (Guía Completa)

### Objeción #1: "No tenemos presupuesto"

**Respuesta A (Piloto gratis)**:
```
"Entiendo. Por eso diseñamos el piloto sin costo:
- 60 días GRATIS (hardware + software + soporte)
- Ustedes solo invierten: tiempo de sus médicos (4h capacitación día 1)
- Si no funciona, retiramos equipo y fin
- Si funciona, podemos hacer leasing desde $2,900/mes (más barato que 1 día de médico)

No estamos pidiendo budget AHORA, solo 60 días de prueba. ¿Les parece razonable?"
```

**Respuesta B (ROI)**:
```
"Déjeme ponerlo en perspectiva:

Si tienen 3 médicos que atienden 10 consultas/día c/u = 30 consultas.
Ahorran 6 min/consulta × 30 = 180 min/día = 3 horas libres.

Opciones con esas 3 horas:
1. Atender 6 consultas más/día × $500 = $3,000/día × 20 días = $60,000/mes
2. O reducir 1 turno de médico = ahorrar $30,000-$50,000/mes

Leasing es $2,900/mes. Se paga solo 10 veces. ¿No es una inversión razonable?"
```

**Respuesta C (Timing)**:
```
"Entiendo que 2025 ya está cerrado. ¿Qué tal si hacemos el piloto gratis AHORA, y si funciona, ustedes presupuestan para 2026?

Así llegan a enero con:
- Piloto validado
- Médicos entrenados
- Caso de negocio claro (con data de los 60 días)
- Decisión más fácil para aprobar presupuesto

¿Tiene sentido?"
```

---

### Objeción #2: "Ya tenemos un EMR / No queremos cambiar sistemas"

**Respuesta**:
```
"Perfecto, no estamos pidiendo que reemplacen su EMR.

Free Intelligence Cold es un ASISTENTE, no un reemplazo:
1. IntakeCoach recopila información conversacionalmente (2 min)
2. Sistema genera SOAP note
3. Médico valida y copia/pega al EMR existente

Es un paso ANTES del EMR, no en lugar de él.

En el futuro (Fase 2) podemos integrar directamente con su EMR vía API, pero el piloto funciona standalone. ¿Tiene sentido?"
```

---

### Objeción #3: "¿Qué tan precisa es la IA? ¿Y si se equivoca?"

**Respuesta**:
```
"Excelente pregunta. Déjeme ser claro:

❌ La IA NO diagnostica
❌ La IA NO prescribe tratamiento
✅ La IA ASISTE en documentación

El flujo es:
1. IA recopila información del paciente (como un asistente humano)
2. IA sugiere clasificación de urgencia (LOW/MODERATE/HIGH/CRITICAL)
3. IA genera BORRADOR de SOAP note
4. **MÉDICO valida TODO** (puede editar 100% del contenido)
5. Médico confirma, y ENTONCES se guarda

El médico SIEMPRE tiene última palabra. La IA es como un residente muy rápido que hace el draft, pero el médico es quien firma.

¿Eso responde su preocupación?"
```

---

### Objeción #4: "No tenemos tiempo para implementar / Muy ocupados"

**Respuesta**:
```
"Justamente por eso diseñamos implementación express:

**Día 1** (único día que requiere su tiempo):
- Mañana (4h): Instalación técnica (nosotros lo hacemos, IT solo supervisa)
- Tarde (4h): Capacitación médicos + staff (hands-on training)
- Total: 1 día, 8 horas de su equipo

**Día 2-60**:
- Sistema funciona solo
- Soporte remoto <24h response
- NO requiere dedicación extra

Literalmente es 1 día de inversión para potencialmente ahorrar 2-3 horas/día los siguientes 60 días (120-180 horas ahorradas).

Incluso si solo funciona al 50%, siguen ganando 60 horas. ¿No vale la pena 8 horas de inversión?"
```

---

### Objeción #5: "Necesito consultar con IT / Legal / Dirección"

**Respuesta A (Facilitar)**:
```
"Por supuesto. Es una decisión importante.

¿Qué tal si hacemos esto?
1. Hoy: Le envío one-pager + requisitos técnicos + LOI template
2. Usted comparte con IT/Legal/Dirección internamente
3. Coordinamos un call de 30 min con todo el equipo (IT, Legal, Médico, Finanzas)
4. Yo respondo todas sus preguntas técnicas/legales/comerciales
5. Si todos están de acuerdo, firmamos LOI

¿Le parece? ¿Cuándo podríamos tener ese call grupal?"
```

**Respuesta B (Reducir fricción)**:
```
"Entiendo. ¿Me puede ayudar a entender qué específicamente necesitan validar?

- **IT**: ¿Requisitos técnicos? (tenemos spec completo)
- **Legal**: ¿Compliance? (LOI incluye cláusulas de confidencialidad + ownership de datos)
- **Finanzas**: ¿Budget? (piloto es gratis, producción tiene 2 opciones de pago)

Si me dice qué es más crítico, puedo enviarle documentación específica para acelerar la decisión interna."
```

---

### Objeción #6: "¿Qué pasa si se cae el sistema en medio de una consulta?"

**Respuesta**:
```
"Buena pregunta. Tenemos 3 capas de resiliencia:

1️⃣ **Offline-first**: Sistema funciona SIN internet
   - LLM (Ollama) corre localmente
   - Event store (HDF5) es local
   - Si se cae internet, sistema sigue funcionando

2️⃣ **Append-only**: Datos nunca se pierden
   - Cada interacción se guarda inmediatamente
   - Si sistema se reinicia, recupera estado completo
   - Es como un DVR médico (graba todo, siempre)

3️⃣ **Fallback manual**: Si sistema totalmente caído
   - Médico hace intake manual (como siempre)
   - Cuando sistema regresa, puede ingresar datos retroactivamente

En el piloto, métricas de uptime son >95%. Si caemos de eso, es motivo para terminar piloto sin costo. ¿Le parece justo?"
```

---

### Objeción #7: "Prefiero esperar a que el producto madure más"

**Respuesta**:
```
"Entiendo la precaución. Pero déjeme compartirle por qué AHORA es buen momento:

1️⃣ **Early adopter advantage**:
   - Primeros 5 pilotos: 20% descuento + upgrade hardware gratis
   - Su feedback influye roadmap (features que ustedes necesiten)
   - Caso de éxito (si funciona, son referencia en la industria)

2️⃣ **Piloto sin riesgo**:
   - 60 días gratis, si no funciona, fin
   - Worst case: perdieron 8 horas (capacitación día 1)
   - Best case: resuelven problema de documentación por años

3️⃣ **Competencia**:
   - Otros hospitales YA están probando soluciones de IA
   - Quien adopte primero, tiene ventaja operativa (más pacientes, menos costo)

Si esperan 6-12 meses, el producto estará más maduro, pero:
- Ya no habrá descuento early adopter
- Otros hospitales ya tendrán ventaja
- El problema de documentación sigue costando 40% del tiempo

¿Cuál es su preocupación específica sobre madurez? Tal vez puedo resolverla."
```

---

## 📊 Deal Structure (Checklist)

### Piloto (60 días sin costo)

**Incluido**:
- ✅ Hardware demo (DELL Latitude 7430 o servidor cliente)
- ✅ Software FI-Cold (licencia temporal)
- ✅ Implementación on-site (Día 1, 4-6h)
- ✅ Capacitación (Día 1, 4h)
- ✅ Soporte remoto (<24h response)
- ✅ Reportes semanales (uso, uptime, incidencias)
- ✅ Reporte final (Día 60, métricas + recomendaciones)

**Excluido**:
- ❌ Internet del cliente (deben tener LAN)
- ❌ On-site support después de Día 1 (solo remoto)
- ❌ Customizaciones específicas del cliente
- ❌ Integración con EMR existente (Fase 2)

**Métricas de éxito** (para considerar piloto exitoso):
- Uptime >95%
- Response time <3s
- SOAP notes generadas ≥30
- Satisfacción médicos ≥4/5
- Tiempo ahorrado ≥30%

### Producción (post-piloto)

**Opción A: Compra**
- Hardware: $85,000 MXN
- Software: $120,000 MXN
- Implementación: $40,000 MXN
- **Total: $245,000 MXN**
- Soporte anual: $24,000 MXN (año 2+)

**Opción B: Leasing (36 meses)**
- $2,900 MXN/mes × 36 meses = $104,400 MXN
- Todo incluido (hardware + software + soporte)
- Ownership transferido al mes 37

**Descuentos** (primeros 5 pilotos):
- 20% descuento = $196,000 MXN compra (vs $245k)
- O $2,320 MXN/mes leasing (vs $2,900)
- + Upgrade hardware gratis (64GB RAM vs 32GB)

---

## 🎯 Closing Techniques

### Soft Close (durante call)

```
"Si el piloto cumple las métricas que mencionamos (uptime, satisfacción, tiempo ahorrado), ¿ustedes continuarían a producción?"
```

*Si dicen SÍ = strong buy signal. Si dicen "depende" = explorar objeciones.*

---

### Assumptive Close

```
"Perfecto. Entonces les envío el LOI hoy, ustedes lo revisan esta semana, y coordinamos implementación para [fecha]. ¿Les parece?"
```

*Actúa como si ya decidieron. Si no objetan, es SÍ implícito.*

---

### Alternative Close

```
"¿Prefieren empezar el piloto la próxima semana o en 2 semanas? Tengo slots disponibles ambas."
```

*Da opciones, pero ambas asumen que van a empezar.*

---

### Urgency Close (si aplica)

```
"Los primeros 5 pilotos tienen 20% descuento. Llevamos [X] firmados, quedan [5-X] slots. Si firman esta semana, garantizamos el descuento."
```

*Solo usar si es verdad. No inventar urgencia falsa.*

---

### Summary Close

```
"Entonces, recapitulando lo que discutimos:
- Piloto 60 días sin costo ✅
- Implementación Día 1 (8h de su equipo) ✅
- Métricas claras de éxito ✅
- Si funciona, leasing desde $2,900/mes ✅
- ROI esperado <10 meses ✅

¿Hay algo más que necesite para tomar la decisión?"
```

*Resume beneficios + hace última pregunta abierta para objeciones finales.*

---

## 📧 Follow-Up Sequence (Post-Call)

### Email #1: Mismo día (dentro de 2 horas)

**Subject**: Gracias por el call — Materiales FI-Cold

**Body**:
```
Hola [Nombre],

Gracias por los 30 minutos de hoy. Me dio gusto conocer más sobre [Nombre Hospital] y sus retos de documentación.

Como prometí, adjunto:
- 📄 One-pager FI-Cold (1 página, PDF)
- 🎥 Video demo (90 segundos): [link]
- 📋 LOI template (Letter of Intent para piloto 60 días)
- 🛠️ Requisitos técnicos (para compartir con IT)

**Next steps sugeridos**:
1. Revisar materiales esta semana
2. Consultar con [IT / Legal / Dirección] si necesario
3. Call de seguimiento [fecha propuesta]: ¿[Día X] a las [hora] o [Día Y] a las [hora]?

Si tienen preguntas antes, pueden responder este email o llamarme al [teléfono].

Saludos,
[Tu Nombre]
Free Intelligence
[email]
[teléfono]
```

**Attachments**:
- FI-COLD-ONE-PAGER.pdf
- LOI-TEMPLATE.pdf (opcional si ya mencionaron interés)

---

### Follow-Up #2: Día 3 (si no responden)

**Subject**: Re: Gracias por el call — ¿Dudas?

**Body**:
```
Hola [Nombre],

¿Tuvieron chance de revisar los materiales que envié?

¿Hay alguna duda que pueda resolver? ¿O necesitan algo adicional para tomar la decisión?

También puedo coordinar un call con IT/Legal si ayuda.

Quedo al pendiente.
Saludos,
[Tu Nombre]
```

---

### Follow-Up #3: Día 7 (si no responden)

**Subject**: Re: Gracias por el call — ¿Cerramos este tema?

**Body**:
```
Hola [Nombre],

No he tenido respuesta. Imagino que:
a) No es prioritario ahora
b) Decidieron no continuar
c) Están ocupados y no han tenido tiempo de revisar

Si es (a) o (b), sin problema. ¿Me confirmas para cerrar este contacto?

Si es (c) y SÍ les interesa, responde con "DEMO" y coordinamos el siguiente paso.

Gracias!
[Tu Nombre]
```

---

## 📈 Pipeline Stages & Conversion Rates

```
100 leads contactados (Tier 1+2)
  → 67 responden (67% response rate)
  → 50 intro calls agendados (75% booking rate)
  → 35 calls completados (70% show rate)
  → 20 propuestas enviadas (57% interest rate)
  → 10 pilotos firmados (50% close rate)
  → 7 pilotos implementados (70% implementation rate)
  → 4 conversiones a producción (57% conversion rate)
```

**Meta primer trimestre** (90 días):
- 30-50 leads contactados
- 10 intro calls agendados
- 7 calls completados
- 4 propuestas enviadas
- 2 pilotos firmados
- 2 pilotos implementados

**Meta segundo trimestre** (días 91-180):
- 1 conversión a producción (de pilotos Q1)
- 3 pilotos nuevos firmados
- Total acumulado: 5 pilotos, 1 cliente producción

---

## 🔗 Related Documents

- **Leads Database**: `LEADS-DATABASE.md` (50 leads con contactos)
- **Outreach Sequence**: `OUTREACH-SEQUENCE.md` (7 touchpoints)
- **One-pager**: `FI-COLD-ONE-PAGER.md` (adjuntar en emails)
- **LOI Template**: `LOI-TEMPLATE.md` (enviar si interesados)
- **SOW Template**: `SOW-TEMPLATE.md` (enviar con LOI)
- **Demo Script**: `DEMO-SCRIPT-VAR.md` (para demos presenciales)
- **KPIs**: `FI-COLD-KPIS.md` (métricas de éxito)

---

**Status**: Playbook completo ✅
**Próximo paso**: Entrenar vendedor fraccional con este script
**Owner**: Bernard Uriza Orozco
**Última actualización**: 2025-10-28
