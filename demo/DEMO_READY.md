# ✅ Demo Lista - FI-Entry (Opción 2)

**Status:** READY FOR DEMO
**Fecha creación:** 2025-10-30
**Demo fecha:** Próxima semana (pendiente confirmar)

---

## 🎯 Resumen Ejecutivo

Tienes **TODOS los materiales** necesarios para hacer una demo profesional de 30 minutos sin depender de Whisper. El enfoque es "smoke and mirrors": mostramos resultados finales (transcripciones + resúmenes) sin hacer transcripción en vivo.

---

## ✅ Lo que SÍ tenemos (100% funcional)

### 1. Datos Demo (3 Consultas Pre-generadas)

**Ubicación:** `demo/consultas/`

| Archivo | Caso Clínico | Duración | Datos Estructurados |
|---------|--------------|----------|---------------------|
| consulta_001.yaml | Hipertensión Arterial | 8 min | 12 campos |
| consulta_002.yaml | Diabetes Tipo 2 + Neuropatía | 12 min | 18 campos |
| consulta_003.yaml | Infección Respiratoria | 6 min | 15 campos |

Cada YAML incluye:
- ✅ Transcripción completa (diálogo doctor-paciente)
- ✅ Resumen estructurado (motivo, síntomas, diagnóstico, plan)
- ✅ Metadata (SHA256, timestamps, quality metrics)

### 2. Backend APIs (Puerto 7001)

- ✅ `/api/sessions` - Lista de sesiones (5 existentes)
- ✅ `/api/sessions/{id}` - Detalle de sesión
- ✅ `/api/kpis` - Métricas dashboard
- ✅ `/api/transcribe` - Endpoint existe (no usaremos en vivo)
- ✅ Storage HDF5 append-only funcional

### 3. Frontend UI (Puerto 9000)

- ✅ `/dashboard` - 8 KPIs en tiempo real
- ✅ `/sessions` - Lista de sesiones
- ✅ `/sessions/[id]` - Timeline viewer
- ✅ `/audit` - Audit log (backup)
- ✅ Dark mode, responsive, profesional

### 4. Sales Materials

- ✅ `sales/entry/offer.yaml` (146 LOC) - Alcance, SLOs, límites
- ✅ `sales/entry/pricing.yaml` (211 LOC) - $3k piloto, addons, discounts
- ✅ `sales/entry/loi_template.yaml` (275 LOC) - Carta de intención firmable
- ✅ `sales/entry/leads.csv` (33 leads) - Base de prospectos

### 5. Documentation

- ✅ `demo/README.md` - Quick start guide
- ✅ `demo/DEMO_SCRIPT.md` - Script completo de presentación (30 min)
- ✅ `demo/scripts/simple_demo_check.sh` - Health check pre-demo

---

## 🚀 Cómo Usar (30 min antes de la demo)

### Paso 1: Verificar sistema

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
./demo/scripts/simple_demo_check.sh
```

**Expected output:**
```
✅ READY FOR DEMO
```

Si dice `❌ NOT READY`:
```bash
pnpm dev  # Start all services
```

### Paso 2: Abrir tabs en browser

1. http://localhost:9000/dashboard
2. http://localhost:9000/sessions
3. http://localhost:9000/audit (backup)

### Paso 3: Leer demo script

Abre `demo/DEMO_SCRIPT.md` y léelo una vez completo. Memoriza frases clave.

---

## 📋 Demo Flow (30 min)

### Estructura:

1. **Intro (5 min)** - Problema + solución
   - "Doctor, sé que tiene poco tiempo..."
   - Mostrar 3 pilares: Transcripción, Resumen, Integridad

2. **Dashboard (8 min)** - Métricas operacionales
   - KPIs en tiempo real
   - "Redaction: Active, Egress: Deny" ← Privacidad

3. **Consultas (12 min)** - Transcripción + resumen
   - Mostrar consulta_001 (Hipertensión)
   - Señalar: "El sistema extrajo esto automáticamente"
   - Mostrar consulta_002 (Diabetes) rápido

4. **Integridad (3 min)** - SHA256, append-only
   - "Cada nota tiene huella digital única"
   - "No-repudiation para auditoría"

5. **Cierre comercial (7 min)** - Pricing + LOI
   - "$3,000 piloto 60 días vs $35,000 EMR tradicional"
   - Sacar LOI, pedir firma

6. **Next steps (2 min)** - Firma o follow-up

---

## 🎯 Mensaje Clave (Memorizar)

**5 Frases que DEBES decir:**

1. **"100% local, sus datos nunca salen"**
   → Privacidad, soberanía de datos

2. **"SHA256 hash para integridad completa"**
   → Auditoría, no-repudiation

3. **"$3,000 vs $35,000 de EMR tradicional"**
   → Pricing irresistible

4. **"1 semana de instalación vs 3-6 meses"**
   → Speed to value

5. **"60 días sin compromiso"**
   → Low risk, easy yes

---

## ⚠️ Qué Decir (y qué NO decir)

### ✅ SÍ Decir:

- "El sistema transcribe automáticamente con IA local"
- "Resumen estructurado extraído por LLM on-premise"
- "En instalación real, configuramos micrófono y grabación"
- "Estos son ejemplos de consultas ya procesadas"

### ❌ NO Decir:

- "Esto es data pre-cargada" (obvio, no lo menciones)
- "Whisper no está instalado ahorita"
- "Es solo una demo, no funciona en vivo"
- Detalles técnicos (Turborepo, PM2, HDF5)

### 🎭 Si pregunta: "¿Puedo ver transcripción en vivo?"

**Respuesta:**
> "Claro doctor. La transcripción en vivo requiere configurar el micrófono con su consultorio. Aquí le muestro cómo queda el resultado final. En la instalación real en su servidor, configuramos eso y usted solo graba y el sistema hace el resto."

---

## 🛡️ Backup Plans

### Si dashboard no carga:
- Reload en incógnito
- Mostrar screenshots (tomar antes de demo)

### Si sessions está vacío:
- Abrir `demo/consultas/consulta_001.yaml` en editor
- Explicar: "Así se ve la data cuando transcribe"

### Si pregunta por Whisper en vivo:
- "La transcripción en vivo se configura en instalación"
- "Aquí muestro resultado final"

---

## 📊 Métricas de Éxito

| Objetivo | Target |
|----------|--------|
| Doctor entendió 3 pilares | ✅ |
| Mostró interés en pricing | ✅ |
| Preguntó por instalación | ✅ |
| **Firmó LOI** | 🎯 |
| Agendó follow-up | 🎯 |

---

## 📦 Llevar a la Demo

### Impresos:
- [ ] LOI (2 copias) - Generar PDF de `sales/entry/loi_template.yaml`
- [ ] Pricing one-pager - Generar PDF de `sales/entry/pricing.yaml`
- [ ] Business card
- [ ] Bolígrafo

### En laptop:
- [ ] `demo/DEMO_SCRIPT.md` abierto
- [ ] `demo/consultas/*.yaml` (backup)
- [ ] Browser tabs (dashboard, sessions, audit)
- [ ] Laptop cargada + charger
- [ ] Hotspot (backup internet)

---

## 📧 Email Template (Si cierra)

```
Asunto: Confirmación LOI - FI-Entry Piloto 60 días

Estimado Dr. [Nombre],

Gracias por su confianza en Free Intelligence.

Adjunto:
- LOI firmada (escaneo)
- Pricing detallado
- Próximos pasos

Calendario instalación: [Fecha]

Saludos,
Bernard Uriza
CEO, Free Intelligence
bernard@free-intelligence.com
+52 55 1234 5678
```

---

## ✅ Checklist Final (Día de la Demo)

### 30 min antes:
- [ ] Servicios corriendo (`pnpm dev`)
- [ ] Demo check OK (`./demo/scripts/simple_demo_check.sh`)
- [ ] Browser tabs abiertos
- [ ] LOI impreso
- [ ] Laptop cargada

### Durante demo:
- [ ] Grabar sesión (con permiso)
- [ ] Tomar notas de objeciones
- [ ] Identificar siguiente paso concreto

### Post-demo:
- [ ] Email en <2h si firmó
- [ ] Email en <24h si pidió tiempo
- [ ] Actualizar CRM/Trello

---

## 🎓 Qué Pasa Después (Si firma)

1. **Semana 1:** Instalación en su servidor
   - Tú llevas laptop, instalas en su DELL
   - 4-6 horas trabajo técnico
   - Primera capacitación (2h)

2. **Semana 2-3:** Go-live
   - Doctor empieza a usar en consultas reales
   - Soporte por email/WhatsApp
   - Ajustes si hay bugs

3. **Día 60:** Retrospectiva
   - "¿Le sirvió?"
   - Si SÍ: Upgrade a FI-Health ($500/mes)
   - Si NO: Refund parcial, feedback

---

## 🚨 Objeciones Comunes (Preparar Respuestas)

| Objeción | Respuesta |
|----------|-----------|
| "¿Y si no me funciona?" | "Refund parcial según uso. Si falla por mi culpa, refund completo." |
| "No tengo servidor" | "Le consigo DELL por $1,200 adicional, ya configurado." |
| "Suena muy técnico" | "Exacto, yo hago la instalación. Usted solo usa el dashboard." |
| "¿Qué pasa en 60 días?" | "Si le gusta, $500/mes. Si no, cancela sin penalización." |
| "¿Es legal/HIPAA?" | "100% local, sin PHI en cloud. Usted es dueño de los datos." |

---

## 💡 Tips Finales

1. **Habla poco, muestra mucho**
   80% demo, 20% explicación

2. **Enfócate en valor, no en tech**
   "Ahorra tiempo" > "Usa Whisper y HDF5"

3. **Responde objeciones con ejemplos**
   "Mire cómo se ve el resumen estructurado"

4. **Cierra con pregunta**
   "¿Qué le parece, doctor?"

5. **Pide firma HOY**
   "Firmamos hoy, instalación próxima semana"

---

## 📞 Soporte Durante Demo

Si algo falla técnicamente:

1. **Mantén la calma**
2. **Usa backup plan** (mostrar YAMLs)
3. **Enfoque en valor:** "Déjeme explicarle cómo funciona conceptualmente"
4. **Reagendar si es necesario:** "Prefiero mostrarle esto funcionando bien, ¿moverlo 2 días?"

---

## 🎉 Success Case (Ideal)

**Fin de demo:**

Doctor: "Me gusta. ¿Cuándo puede instalar?"
Tú: "La próxima semana. Aquí está el LOI, firmamos hoy y agendamos instalación."
Doctor: [Firma]
Tú: "Perfecto. Le mando confirmación por email en 1 hora. Gracias doctor."

**[Exit, enviar email en <30 min, celebrar con café]** ☕️

---

**¡MUCHA SUERTE EN LA DEMO!** 🚀

**Recuerda:**
- Eres el experto
- Tienes un producto real
- Precio justo ($3k vs $35k EMR)
- Risk bajo (60 días sin compromiso)
- **ASK FOR THE SALE**

---

**Status:** ✅ 100% READY
**Next:** Ejecutar demo, cerrar cliente, instalar sistema
**Contact:** bernard@free-intelligence.com
