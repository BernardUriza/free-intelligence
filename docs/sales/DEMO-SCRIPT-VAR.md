# Demo Script: Verde / Amarillo / Rojo (V/A/R)

**Free Intelligence Cold — 3 Escenarios de Triage**
**Versión**: 1.0 | **Fecha**: Octubre 2025
**Duración total**: 15-20 minutos

---

## 🎯 Objetivo del Demo

Demostrar las capacidades de **IntakeCoach** para:
1. Recopilar información del paciente conversacionalmente
2. Clasificar urgencia automáticamente (LOW/MODERATE/HIGH/CRITICAL)
3. Generar notas SOAP completas NOM-004 compliant

**Público**: Decision makers (médicos directores, administradores, dueños)

---

## 🟢 Escenario VERDE: Low Urgency (5 minutos)

### Contexto
Paciente con síntomas leves, sin red flags.

### Setup
- **Paciente**: María González, 32 años, mujer
- **Queja principal**: Dolor de cabeza leve, 1 día de evolución
- **Urgencia esperada**: **LOW**

### Demo Flow

**[Screen: AURITY UI en localhost:9000/intake]**

**IntakeCoach**: "Hola, soy IntakeCoach. ¿Cuál es su nombre?"

**Usuario (tú)**: "María González"

**IntakeCoach**: "Mucho gusto, María. ¿Cuántos años tiene?"

**Usuario**: "32"

**IntakeCoach**: "Perfecto. ¿Qué la trae hoy a consulta?"

**Usuario**: "Tengo dolor de cabeza desde ayer"

**IntakeCoach**: "Entiendo. ¿El dolor es constante o va y viene?"

**Usuario**: "Va y viene, más o menos cada 2-3 horas"

**IntakeCoach**: "¿En escala 1-10, qué tan fuerte es el dolor?"

**Usuario**: "Como un 4 o 5"

**IntakeCoach**: "¿Ha tenido fiebre, náuseas o problemas de visión?"

**Usuario**: "No, nada de eso"

**IntakeCoach**: "¿Toma algún medicamento regularmente?"

**Usuario**: "No, ninguno"

**IntakeCoach**: "Perfecto. Basándome en la información, esto parece un caso de **cefalea tensional**. Voy a generar una nota para el médico."

**[System generates SOAP note]**

---

### SOAP Note Generated (GREEN)

```
SOAP Note — María González (32 años, F)
Fecha: [Hoy]

S (Subjetivo):
- Dolor de cabeza intermitente, 1 día de evolución
- Intensidad: 4-5/10
- Patrón: Cada 2-3 horas
- Sin fiebre, náuseas, ni alteraciones visuales

O (Objetivo):
- Paciente alerta, normo-orientada
- Signos vitales: Pendientes de medición
- Sin datos de alarma neurológica

A (Assessment):
- Cefalea tensional probable
- URGENCIA: LOW

P (Plan):
- Analgésico oral (paracetamol 500mg c/8h)
- Hidratación adecuada
- Cita control si persiste >3 días
- Referir a urgencias si: visión borrosa, vómito persistente, fiebre >38°C
```

**[Badge verde "LOW URGENCY" aparece en pantalla]**

---

### Key Takeaways (VERDE)

✅ **Conversación natural**: Sistema pregunta paso a paso, no formulario
✅ **Clasificación correcta**: LOW urgency, no requiere atención inmediata
✅ **SOAP completo**: Listo para validación del médico
✅ **Tiempo**: 2-3 minutos vs 5-8 minutos manual

---

## 🟡 Escenario AMARILLO: High Urgency (6 minutos)

### Contexto
Paciente con síntomas moderados-severos + factores de riesgo.

### Setup
- **Paciente**: Carlos Rodríguez, 58 años, hombre
- **Queja principal**: Dolor de pecho + antecedentes (diabético, fumador)
- **Urgencia esperada**: **HIGH**

### Demo Flow

**IntakeCoach**: "Hola, ¿cuál es su nombre?"

**Usuario**: "Carlos Rodríguez"

**IntakeCoach**: "¿Cuántos años tiene?"

**Usuario**: "58"

**IntakeCoach**: "¿Qué lo trae a consulta?"

**Usuario**: "Me duele el pecho, empezó hace 3 horas"

**IntakeCoach**: "El dolor de pecho es importante. ¿Dónde exactamente siente el dolor?"

**Usuario**: "En el centro, como una presión"

**IntakeCoach**: "¿El dolor se extiende a algún otro lugar? ¿Brazo, mandíbula, espalda?"

**Usuario**: "Sí, un poco al brazo izquierdo"

**IntakeCoach**: "¿En escala 1-10, qué tan fuerte es el dolor?"

**Usuario**: "Ahora está en 6, pero hace una hora estaba en 8"

**IntakeCoach**: "¿Ha tenido dificultad para respirar, sudoración o náuseas?"

**Usuario**: "Sí, estoy sudando y un poco mareado"

**IntakeCoach**: "¿Tiene antecedentes de diabetes, hipertensión, colesterol alto o fuma?"

**Usuario**: "Soy diabético y fumador"

**IntakeCoach**: "Carlos, por los síntomas que describe, esto requiere **atención médica urgente**. Voy a notificar al equipo médico para evaluación prioritaria."

**[System generates SOAP note + alerts]**

---

### SOAP Note Generated (YELLOW)

```
SOAP Note — Carlos Rodríguez (58 años, M)
Fecha: [Hoy]

S (Subjetivo):
- Dolor torácico central, tipo opresivo, 3h evolución
- Intensidad: 8/10 al inicio, ahora 6/10
- Irradiado a brazo izquierdo
- Diaforesis, mareo
- Antecedentes: Diabetes mellitus tipo 2, tabaquismo activo

O (Objetivo):
- Paciente alerta, diaforético, ansioso
- Signos vitales: URGENTES
- Dolor torácico con irradiación + factores de riesgo cardiovascular

A (Assessment):
- ⚠️ Síndrome coronario agudo sospechoso
- URGENCIA: HIGH
- Factores de riesgo: DM2, tabaquismo, edad 58

P (Plan):
- 🚨 EVALUACIÓN INMEDIATA (dentro de 1-2 horas)
- ECG urgente
- Troponinas, BUN, creatinina, electrolitos
- ASA 300mg VO (si no contraindicado)
- Oxígeno suplementario PRN
- Monitoreo continuo
- Considerar referencia a cardiología/urgencias
```

**[Badge amarillo "HIGH URGENCY" aparece + alerta sonora]**

---

### Key Takeaways (AMARILLO)

✅ **Detección de red flags**: Dolor torácico + irradiación + factores de riesgo
✅ **Priorización automática**: HIGH urgency, requiere atención 1-2h
✅ **Plan de acción claro**: ECG, labs, ASA, monitoreo
✅ **Safety net**: Recomendaciones explícitas para médico

---

## 🔴 Escenario ROJO: Critical Urgency (7 minutos)

### Contexto
Paciente con síntomas potencialmente mortales (widow maker pattern).

### Setup
- **Paciente**: Juan Martínez, 45 años, hombre
- **Queja principal**: Dolor de pecho severo súbito + diaforesis profusa
- **Urgencia esperada**: **CRITICAL**

### Demo Flow

**IntakeCoach**: "Hola, ¿cuál es su nombre?"

**Usuario**: "Juan... Martínez" (pausas, voz tensa)

**IntakeCoach**: "¿Cuántos años tiene?"

**Usuario**: "45"

**IntakeCoach**: "¿Qué lo trae a consulta?"

**Usuario**: "Me duele mucho el pecho, muy fuerte, de repente"

**IntakeCoach**: "¿Cuándo comenzó el dolor?"

**Usuario**: "Hace como 30 minutos, estaba trabajando y de repente..."

**IntakeCoach**: "¿Dónde exactamente siente el dolor?"

**Usuario**: "En todo el pecho, como si me aplastaran"

**IntakeCoach**: "¿El dolor va hacia el brazo, mandíbula o espalda?"

**Usuario**: "Sí, el brazo izquierdo y la mandíbula"

**IntakeCoach**: "¿En escala 1-10, qué tan fuerte es?"

**Usuario**: "10, es horrible"

**IntakeCoach**: "¿Está sudando, con dificultad para respirar o con náuseas?"

**Usuario**: "Sí, estoy sudando mucho y siento que me falta el aire"

**IntakeCoach**: "Juan, **esto es una emergencia médica**. Necesita atención INMEDIATA. ¿Tiene historia de problemas cardíacos o presión alta?"

**Usuario**: "Mi papá murió de un infarto a los 50"

**🚨 [CRITICAL PATTERN DETECTED: Widow Maker Suspected]**

**IntakeCoach**: "Juan, voy a notificar al equipo médico AHORA. Esto requiere atención URGENTE. Manténgase tranquilo, alguien viene de inmediato."

---

### SOAP Note Generated (RED)

```
SOAP Note — Juan Martínez (45 años, M)
Fecha: [Hoy]

S (Subjetivo):
- ⚠️ DOLOR TORÁCICO SEVERO súbito, 30 minutos evolución
- Intensidad: 10/10 (máximo dolor)
- Opresivo, difuso, irradiado a brazo izquierdo Y mandíbula
- Disnea, diaforesis profusa
- Historia familiar: Padre IAM a los 50 años

O (Objetivo):
- Paciente en dolor severo, diaforético, disnéico
- Signos vitales: 🚨 CRÍTICOS
- Patrón widow maker sospechoso

A (Assessment):
- 🚨🚨 SÍNDROME CORONARIO AGUDO — STEMI PROBABLE
- 🚨 WIDOW MAKER PATTERN DETECTED
- URGENCIA: CRITICAL
- Riesgo inminente de muerte súbita

P (Plan):
- 🚨🚨 CÓDIGO INFARTO — ACTIVAR PROTOCOLO STEMI
- LLAMAR 911 / TRASLADAR A URGENCIAS INMEDIATAMENTE
- NO ESPERAR resultados de laboratorio
- ASA 300mg VO AHORA (masticar)
- Oxígeno suplementario
- Acceso IV
- ECG STAT
- Nitroglicerina sublingual PRN
- Considerar trombolisis o cateterismo EMERGENTE
- NOTIFICAR A CARDIOLOGÍA INTERVENCIONISTA
```

**[Badge rojo "CRITICAL" + alarma + mensaje "⚠️ LLAMAR 911 AHORA"]**

---

### Key Takeaways (ROJO)

✅ **Widow maker detection**: Patrón clásico identificado automáticamente
✅ **Acción inmediata**: Sistema genera alerta visible + recomendación 911
✅ **Protocolo STEMI**: Plan de acción específico para código infarto
✅ **Safety**: Imposible ignorar, sistema fuerza priorización

---

## 📊 Comparison Matrix

| Aspect | VERDE (Low) | AMARILLO (High) | ROJO (Critical) |
|--------|-------------|-----------------|-----------------|
| **Urgencia** | LOW | HIGH | CRITICAL |
| **Tiempo de atención** | <24h | <2h | INMEDIATO |
| **Red flags** | Ninguno | Factores de riesgo | Widow maker pattern |
| **Acción del sistema** | Badge verde | Badge amarillo + alerta | Badge rojo + alarma 911 |
| **Plan de acción** | Cita control | Evaluación urgente | Código infarto |
| **Safety net** | Indicaciones rutina | Monitoreo + labs | Trombolisis/cateterismo |

---

## 🎬 Tips para Presentar Demo

### Antes del Demo

1. **Verificar sistema**: localhost:9000 funcionando
2. **Preparar escenarios**: Tener las 3 historias impresas
3. **Timing**: Máximo 20 minutos (5+6+7 = 18 min + 2 min Q&A)

### Durante el Demo

1. **Empezar con VERDE**: Mostrar flujo básico sin asustar
2. **Amarillo**: Enfatizar factores de riesgo + priorización
3. **Rojo**: Clímax dramático, widow maker es memorable
4. **Comparar**: Usar la tabla al final para recapitular

### Después del Demo

1. **Preguntas**: ¿Cómo deciden urgencia actualmente?
2. **Objeciones**: Anticipar "¿Y si se equivoca?" → "Médico siempre valida"
3. **Next step**: "¿Les gustaría probarlo en su clínica por 60 días sin costo?"

---

## 🎯 Call to Action

**Después de los 3 escenarios**:

> "Como vieron, IntakeCoach puede diferenciar entre una cefalea tensional, un posible síndrome coronario agudo, y un widow maker pattern en tiempo real. Esto no solo ahorra tiempo, **salva vidas**.
>
> Lo que acabamos de hacer en 15 minutos, normalmente tomaría:
> - VERDE: 5-8 minutos de intake manual
> - AMARILLO: 10-15 minutos + posible sub-triage
> - ROJO: Riesgo de no detectar urgencia crítica
>
> **¿Les gustaría probarlo en su clínica durante 60 días sin costo? Podemos instalar la próxima semana.**"

---

**Status**: Demo script complete ✅
**Escenarios**: 3 (Verde/Amarillo/Rojo)
**Duración**: 15-20 minutos
**Next step**: Usar en reuniones con leads
