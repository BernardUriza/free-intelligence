# Análisis Competitivo - AURITY

Documento de análisis de competidores y features a incorporar en AURITY.

**Fecha**: 2025-11-21
**Versión**: 0.1.0

---

## Resumen Ejecutivo

Este documento identifica oportunidades de mejora para AURITY basándose en el análisis de competidores en el espacio de IA médica y documentación clínica.

---

## 1. NotaSalud

**URL**: https://www.notasalud.com/
**Tipo**: Asistente IA para notas médicas (SaaS)

### Características Principales
- Graba sesiones con pacientes desde el teléfono
- Genera documentos basados en directrices médicas
- IA que aprende el estilo, formato y plantillas del usuario
- Genera recetas médicas
- Resume sesiones médicas
- App móvil próximamente (iOS/Android)

### Testimonios de Usuarios
> "Tengo más tiempo para mis pacientes y menos tiempo en la computadora."
> "Mis pacientes tienen notas detalladas de cada sesión y yo menos preguntas que responder."

### ✅ Features a Incorporar en AURITY

| Feature | Prioridad | Descripción | Complejidad |
|---------|-----------|-------------|-------------|
| **Generación de Recetas** | 🔴 Alta | Generar recetas médicas automáticamente desde la consulta | Media |
| **IA que aprende estilo** | 🟡 Media | El sistema aprende preferencias de formato/estilo del médico | Alta |
| **App móvil nativa** | 🟡 Media | iOS/Android para grabar consultas desde el teléfono | Alta |

### Notas de Implementación

#### Generación de Recetas
- Integrar con catálogo de medicamentos (ej. Vademécum)
- Validación de dosis e interacciones
- Formato PDF exportable
- Firma digital del médico
- QR de verificación

---

## 2. Telepatía AI

**URL**: https://www.telepatia.ai/
**Tipo**: Asistente IA para documentación médica (SaaS)
**Origen**: Colombia
**Tracción**: 15 instituciones, 250+ médicos

### Características Principales
- Transcripción de conversaciones médico-paciente
- Notas SOAP automáticas (sugerencias que el médico aprueba)
- Traducción de términos médicos automática
- Integración con sistemas EHR existentes
- Multiplataforma: móvil, tablet, computadora
- Cumplimiento HIPAA y LGPD
- Cifrado de extremo a extremo
- Entrenado con guías clínicas

### Testimonios de Usuarios
> "Cambió completamente mi vida al eliminar todo el tecleo durante las consultas." - Dr. Simón Pérez
> "Dejé de estar pegada a la computadora, finalmente pude mirar a mis pacientes a los ojos." - Dra. Cristina Vélez

### Métricas de Impacto
- **+2 horas/día** ahorro por médico
- Reducción de burnout médico
- Menor carga cognitiva

### ✅ Features a Incorporar en AURITY

| Feature | Prioridad | Descripción | Complejidad |
|---------|-----------|-------------|-------------|
| **Integración EHR** | 🔴 Alta | Conectar con sistemas de expediente electrónico existentes | Alta |
| **Traducción términos médicos** | 🟢 Baja | Auto-traducir jerga médica a lenguaje paciente | Baja |
| **Flujo de aprobación** | 🟡 Media | Médico revisa/aprueba sugerencias de IA antes de guardar | Media |
| **Métricas de ahorro** | 🟢 Baja | Dashboard mostrando tiempo ahorrado por médico | Baja |

### Notas de Implementación

#### Integración EHR
- Investigar estándares HL7 FHIR
- APIs para Epic, Cerner, sistemas locales
- Exportar notas en formato compatible

#### Flujo de Aprobación
- AURITY ya tiene notas SOAP, agregar paso de "revisión"
- UI para aceptar/modificar/rechazar sugerencias
- Historial de cambios del médico

---

## 3. [Próximo Competidor]

*Pendiente de análisis...*

---

## Matriz Comparativa General

| Feature | AURITY | NotaSalud | Telepatía | Comp. 4 |
|---------|--------|-----------|-----------|---------|
| Notas SOAP | ✅ | ✅ | ✅ | - |
| Transcripción audio | ✅ | ✅ | ✅ | - |
| Recetas | ❌ | ✅ | ❌ | - |
| IA aprende estilo | ❌ | ✅ | ❌ | - |
| App móvil | PWA | 🔜 | ✅ | - |
| Integración EHR | ❌ | ❌ | ✅ | - |
| Cumplimiento HIPAA | ✅ | ⚠️ | ✅ | - |
| Auditoría inmutable | ✅ | ❌ | ❌ | - |
| White label on-prem | ✅ | ❌ | ❌ | - |
| Timeline causal | ✅ | ❌ | ❌ | - |

---

## Roadmap de Features Sugerido

### Fase 1 - Quick Wins
- [ ] Generación de recetas médicas
- [ ] Métricas de ahorro de tiempo por médico
- [ ] Traducción automática de términos médicos

### Fase 2 - Mejoras UX
- [ ] IA que aprende estilo del médico
- [ ] Templates personalizados por especialidad
- [ ] Flujo de aprobación de notas (revisar antes de guardar)

### Fase 3 - Integraciones
- [ ] Integración con sistemas EHR (HL7 FHIR)
- [ ] App móvil nativa (iOS/Android)

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2025-11-21 | Análisis inicial: NotaSalud |
| 2025-11-21 | Agregado: Telepatía AI |

