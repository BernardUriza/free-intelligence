# Script de Presentación - Demo Doctor
**Duración:** 30-35 minutos
**Audiencia:** Doctor con consulta privada
**Objetivo:** Cerrar piloto de 60 días ($3,000 USD)

---

## Pre-Demo Checklist (30 min antes)

```bash
# 1. Cargar datos demo
cd /Users/bernardurizaorozco/Documents/free-intelligence
python3 demo/scripts/load_demo_data.py

# 2. Iniciar servicios
pnpm dev

# 3. Verificar que todo corre
# Backend: http://localhost:7001/health
# Frontend: http://localhost:9000

# 4. Abrir tabs en browser
# Tab 1: http://localhost:9000/dashboard
# Tab 2: http://localhost:9000/sessions
# Tab 3: http://localhost:9000/audit (backup)
```

---

## Estructura de la Demo (30 min)

### 1. Introducción (5 min)

**Abrir con el problema:**
> "Doctor, sé que tiene poco tiempo, así que voy directo al grano. Usted me comentó que quiere transcribir consultas, tener un resumen automático, y guardar esos datos de manera íntegra. ¿Correcto?"

**[Esperar confirmación]**

> "Perfecto. Lo que le voy a mostrar hoy es **FI-Entry**: un sistema que corre 100% en SU servidor, SUS datos nunca salen a internet, y todo queda guardado con hash SHA256 para integridad completa."

**Tres puntos clave:**
1. **Transcripción automática** de audio a texto
2. **Resumen estructurado** con IA local (sin mandar datos a la nube)
3. **Almacenamiento íntegro** append-only con auditoría completa

---

### 2. Demo Live - Dashboard (8 min)

**[Abrir Tab 1: Dashboard]**

> "Primero, déjeme mostrarle el dashboard. Aquí ve en tiempo real cómo va su sistema."

**Señalar KPIs (pantalla compartida):**

📊 **Métricas Operacionales:**
- **Sessions Today**: "Cuántas consultas ha capturado hoy"
- **Total Interactions**: "Total de eventos desde que instaló"
- **p95 Ingestion API**: "Qué tan rápido guarda los datos (meta: <2 segundos)"
- **Cache Hit Ratio**: "Eficiencia del sistema"

🔒 **Seguridad & Privacidad:**
- **Redaction Status: Active** → "PII/PHI se redacta automáticamente si se detecta"
- **Egress Policy: Deny** → "Nada sale a internet, todo local"

> "Doctor, esto es importante: el sistema está configurado para NO mandar nada a la nube. Todo queda aquí, en su servidor."

**[Pausa para preguntas - max 2 min]**

---

### 3. Demo Live - Consultas (12 min)

**[Abrir Tab 2: Sessions]**

> "Ahora déjeme mostrarle consultas reales. Cargué 3 ejemplos de mi consulta para que vea cómo se ve."

**Señalar lista de sesiones:**
- Consulta 001: Hipertensión Arterial
- Consulta 002: Diabetes Tipo 2
- Consulta 003: Infección Respiratoria

> "Cada sesión tiene un ID único, timestamp, y puede ver cuántas interacciones hay."

**[Click en Consulta 001 - Hipertensión]**

**Mostrar transcripción:**
> "Mire, aquí está la transcripción completa de la consulta. El sistema grabó el audio y lo transcribió automáticamente con Whisper (modelo local, sin internet)."

**[Scroll por la transcripción]**

> "Y aquí está lo importante: el resumen estructurado."

**Señalar secciones del resumen:**
1. **Motivo de consulta**: "Seguimiento de hipertensión arterial"
2. **Síntomas reportados**: "Cefalea matutina, presión torácica"
3. **Signos vitales**: "PA 145/95 mmHg"
4. **Diagnóstico**: "HTA no controlada (I10)"
5. **Plan de tratamiento**:
   - Farmacológico: "Losartán 100mg (incremento de dosis)"
   - No farmacológico: "Dieta hiposódica, monitoreo domiciliario"
6. **Seguimiento**: "2 semanas"

> "Fíjese doctor: esto NO lo escribió usted. El sistema lo extrajo automáticamente de la conversación con IA local. Usted solo habla con su paciente, el sistema hace el resto."

**[Pausa para impacto - 10 segundos]**

**[Regresar a lista, click en Consulta 002 - Diabetes]**

> "Déjeme mostrarle otra. Esta es diabetes tipo 2..."

**[Scroll rápido por transcripción y resumen]**

> "Vea: mismo formato estructurado. Motivo, síntomas, diagnóstico, plan. Si usted tiene 10 consultas al día, al final de la semana tiene 50 notas estructuradas, todas guardadas con integridad completa."

---

### 4. Integridad & Auditoría (3 min)

**[Regresar a Sessions, señalar botón Export]**

> "Ahora, la parte de integridad. Doctor, usted me dijo que quiere guardar los datos de manera íntegra. Mire esto:"

**[Click en Export (si está implementado) o explicar:]**

> "Cada consulta tiene un hash SHA256. Es como una huella digital única. Si alguien modifica aunque sea una coma de la transcripción, el hash cambia. Eso le da **no-repudiation**: usted puede demostrar que esta nota es exactamente como quedó el día de la consulta."

> "Además, el sistema es **append-only**: nunca se borran datos, solo se agregan. Si necesita corregir algo, crea una nueva entrada, pero la original queda intacta."

**[Pausa para preguntas - max 2 min]**

---

### 5. Cierre Comercial (7 min)

**Resumir valor:**
> "Recapitulando, doctor:"
> 1. ✅ **Transcripción automática** → Ahorra tiempo de escribir notas
> 2. ✅ **Resumen estructurado** → IA local extrae lo importante
> 3. ✅ **Almacenamiento íntegro** → SHA256, append-only, auditoría completa
> 4. ✅ **100% local** → Sus datos nunca salen de su servidor
> 5. ✅ **Sin PHI en la nube** → Zero risk de brechas de seguridad

**Pricing (sacar LOI):**
> "El piloto de 60 días es $3,000 dólares flat. Sin costos recurrentes mensuales. Sin contrato multi-año. Solo 60 días para que lo pruebe."

**¿Qué incluye?**
- Instalación en su servidor (usted proporciona el hardware o yo se lo consigo por $1,200 adicionales)
- Configuración completa
- 2 sesiones de capacitación
- Soporte por email durante 60 días

**Comparación rápida:**
> "Un EMR tradicional le cuesta entre $12,000 y $35,000 dólares, toma 3-6 meses de implementación, y muchos mandan sus datos a la nube. Esto es $3,000, 1 semana de instalación, 100% local."

**Pregunta de cierre:**
> "Doctor, ¿qué le parece? ¿Tiene alguna pregunta técnica o sobre el pricing?"

**[Esperar respuesta]**

**Si dice que sí:**
> "Perfecto. Aquí tengo la carta de intención (LOI). Es no-binding, solo documenta lo que acordamos. Firmamos hoy, hago la instalación la próxima semana, y en 1 semana ya está usando esto en consulta real."

**Si tiene dudas:**
> "Entiendo. ¿Qué le preocupa específicamente? [Escuchar y responder]"

**Posibles objeciones:**

| Objeción | Respuesta |
|----------|-----------|
| "¿Y si no me funciona?" | "Si en 60 días decide que no le sirve, hay refund parcial según lo que se haya usado. Pero si falla por mi culpa (instalación, bugs), refund completo." |
| "No tengo servidor" | "Le consigo un DELL PowerEdge T40 por $1,200 adicionales. Ya viene configurado, solo lo conecta a su red." |
| "¿Qué pasa después de 60 días?" | "Si le gusta, upgrade a FI-Health: $500/mes con más capacidad y soporte extendido. Si no, cancela sin penalización." |
| "Suena muy técnico" | "Exacto, por eso yo hago la instalación. Usted solo usa el dashboard, yo me encargo de lo técnico." |

---

### 6. Next Steps (2 min)

**Si firma LOI:**
1. ✅ LOI firmada hoy
2. 📧 Email con confirmación y detalles técnicos
3. 📅 Agendar instalación (1 semana max)
4. 🎓 Primera sesión de capacitación (2h)
5. 🚀 Go-live: empieza a usar en consultas reales

**Si pide tiempo:**
> "Sin problema. Le mando por email el LOI, el pricing detallado, y este mismo demo grabado. ¿Cuándo podríamos tener respuesta?"

---

## Backup Plans (Si algo falla)

### Si dashboard no carga:
> "Ah, el navegador cache. Déjeme abrir en incógnito." [Reload]
> Si sigue sin funcionar: "Voy a mostrarle con screenshots que tengo aquí."

### Si no hay datos en sessions:
> "Parece que el script de demo no corrió. Déjeme explicarle con los YAMLs que tengo."
> [Abrir demo/consultas/consulta_001.yaml en editor]

### Si pregunta por Whisper en vivo:
> "La transcripción en vivo requiere micrófono configurado. En la instalación real en su consultorio, configuramos eso. Aquí le muestro cómo queda el resultado final."

---

## Post-Demo (Inmediato)

1. **Si firmó LOI:**
   - Escanear LOI firmada
   - Enviar confirmación por email en <30 min
   - Agendar instalación en Calendly
   - Crear card en Trello: "Cliente: [Nombre] - Instalación [Fecha]"

2. **Si pidió tiempo:**
   - Enviar email en <2h con:
     - PDF del LOI
     - Pricing.yaml como PDF
     - Link a demo grabada (si existe)
     - Next step: "¿Podemos agendar follow-up en 48h?"

3. **Si dijo NO:**
   - Agradecer tiempo
   - Preguntar: "¿Qué tendría que cambiar para que le interesara?"
   - Feedback para mejorar pitch

---

## Métricas de Éxito

✅ **Demo exitosa si:**
- Doctor entendió los 3 pilares (transcripción, resumen, integridad)
- Preguntó por pricing
- Mostró interés en next steps

🎯 **Cerrado si:**
- Firmó LOI
- O agendó call de follow-up en <1 semana

---

## Frases Clave (Memorizar)

1. **"100% local, sus datos nunca salen"** ← Privacidad
2. **"SHA256 hash para integridad completa"** ← Auditoría
3. **"$3,000 vs $35,000 de EMR tradicional"** ← Precio
4. **"1 semana de instalación vs 3-6 meses"** ← Speed
5. **"60 días sin compromiso"** ← Low risk

---

## Documentos Necesarios

- [ ] LOI impreso (2 copias)
- [ ] Pricing one-pager (PDF)
- [ ] Business card
- [ ] Laptop cargada
- [ ] Internet/hotspot backup
- [ ] Bolígrafo para firmar

---

## Contacto Post-Demo

**Email template (si firmó):**
```
Asunto: Confirmación LOI - FI-Entry Piloto 60 días

Estimado Dr. [Nombre],

Gracias por su confianza en Free Intelligence.

Adjunto:
- LOI firmada (escaneo)
- Detalles de instalación
- Calendly para agendar capacitación

Próximos pasos:
1. Instalación: [Fecha]
2. Capacitación: [Fecha]
3. Go-live: [Fecha]

Cualquier pregunta, respondo en <24h.

Saludos,
Bernard Uriza
CEO, Free Intelligence
bernard@free-intelligence.com
+52 55 1234 5678
```

---

**¡ÉXITO EN LA DEMO!** 🚀
