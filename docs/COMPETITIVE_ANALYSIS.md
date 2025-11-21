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

## 3. Leona Health

**URL**: https://www.leona.health/
**Tipo**: Gestión de comunicación médico-paciente vía WhatsApp
**Origen**: México
**Enfoque**: Diferente a los anteriores - no es transcripción de consultas

### Características Principales
- **Integración WhatsApp**: Separa chats de pacientes de personales
- **Transcripción de audios**: Convierte notas de voz a texto
- **Respuestas sugeridas**: IA sugiere respuestas a mensajes
- **Mensajes programados**: Recordatorios automáticos de citas
- **Delegación a equipo**: Asignar mensajes al asistente/equipo médico
- **Historial centralizado**: Notas del equipo siempre disponibles
- **Importación automática**: Recupera últimos 6 meses de chats

### Problema que Resuelve
> Médicos en México dependen mucho de WhatsApp para atender pacientes. Se saturan con notificaciones, mensajes a deshoras y presión de responder inmediatamente con una herramienta no diseñada para medicina.

### ✅ Features a Incorporar en AURITY

| Feature | Prioridad | Descripción | Complejidad |
|---------|-----------|-------------|-------------|
| **Integración WhatsApp** | 🟡 Media | Canal de comunicación paciente vía WhatsApp Business API | Alta |
| **Mensajes programados** | 🟢 Baja | Recordatorios automáticos de citas/seguimiento | Baja |
| **Respuestas sugeridas** | 🟡 Media | IA sugiere respuestas a preguntas frecuentes de pacientes | Media |

### Notas de Implementación

#### Integración WhatsApp
- WhatsApp Business API (requiere aprobación Meta)
- Alternativa: Twilio para WhatsApp
- Separar contexto clínico del chat personal
- Cumplimiento de privacidad en mensajería

---

## 4. Itaca AI

**URL**: https://itaca.ai/
**Tipo**: Asistente IA médica completo (SaaS)
**Origen**: Latinoamérica
**Tracción**: 20,000+ profesionales de salud en LATAM

### Características Principales
- **Notas desde videollamadas**: Integración con Google Meet, Zoom, Microsoft Teams
- **Templates por especialidad**: Psiquiatría, pediatría, cirugía, gineco-obstetricia, medicina interna, urgencias, nutrición
- **Formato SOAP**: Notas estructuradas listas para EHR
- **Respuestas clínicas con citas**: Cada respuesta tiene fuentes verificadas
- **Transcripción presencial**: También funciona en consultas físicas
- **Gestión de casos médicos**: Ecosistema completo

### Testimonios
> "Las consultas a distancia llegaron para quedarse. Esta herramienta permite al médico concentrarse en el paciente mientras la IA se encarga de la documentación." - Dr. José Alfredo Puentes López, Director Médico de Itaca

### Diferenciador Clave
Adaptación automática por especialidad: la nota se ajusta a la terminología y estructura de cada disciplina médica.

### ✅ Features a Incorporar en AURITY

| Feature | Prioridad | Descripción | Complejidad |
|---------|-----------|-------------|-------------|
| **Integración videollamadas** | 🔴 Alta | Conectar con Zoom/Meet/Teams para grabar consultas | Alta |
| **Templates por especialidad** | 🔴 Alta | Notas adaptadas a cada especialidad médica | Media |
| **Citas en respuestas** | 🟡 Media | Incluir fuentes verificadas en respuestas de IA | Media |

### Notas de Implementación

#### Integración Videollamadas
- API de Zoom/Meet para grabar sesiones
- Procesar audio post-llamada
- Alternativa: extensión de navegador que captura audio

#### Templates por Especialidad
- Crear plantillas SOAP específicas:
  - Psiquiatría: estado mental, medicación psiquiátrica
  - Pediatría: percentiles, vacunas, desarrollo
  - Ginecología: ciclo menstrual, embarazo
  - Cirugía: procedimiento, complicaciones
  - Urgencias: triaje, signos vitales
- Selector de especialidad en UI

---

## 5. Dorascribe

**URL**: https://dorascribe.ai/es/
**Tipo**: Scribe médico IA (SaaS)
**Origen**: Internacional
**Idiomas**: Español, francés, portugués, italiano (nativo)

### Características Principales
- **Transcripción en tiempo real**: Escucha y convierte voz a notas
- **Notas SOAP**: Resumen estructurado para copiar/pegar en EMR
- **Plantillas personalizables**: SOAP, H&P, resúmenes de alta
- **App móvil completa**: Misma funcionalidad que desktop
- **Multi-idioma nativo**: 4 idiomas sin traducción
- **Precisión 99%+**: Para grabaciones claras
- **HIPAA compliant**: Cifrado robusto, notas se borran en 28 días

### Planes y Precios (Referencia de mercado)

| Plan | Precio | Transcripciones/mes |
|------|--------|---------------------|
| Free | $0 | 20 |
| Essential | $39/usuario | 150 |
| Professional | $59/usuario | 250 |
| Premium | $89/usuario | Ilimitadas |

*Descuento anual: 2 meses gratis*

### Dato Clave
> Los médicos pasan casi **2 horas en documentación por cada hora de atención** directa al paciente.

### ✅ Features a Incorporar en AURITY

| Feature | Prioridad | Descripción | Complejidad |
|---------|-----------|-------------|-------------|
| **Plan gratuito limitado** | 🟡 Media | Freemium para captar usuarios (20 transcripciones/mes) | Baja |
| **Multi-idioma nativo** | 🟢 Baja | Soporte nativo para español, portugués, etc. | Media |
| **Plantillas personalizables** | 🟡 Media | Usuario puede modificar campos/secciones de templates | Media |
| **Auto-completado** | 🟢 Baja | Sugerencias para entradas repetitivas | Baja |

### Notas de Implementación

#### Modelo Freemium
- 20 sesiones gratis/mes para usuarios nuevos
- Upgrade a planes pagados para más volumen
- Referencia de pricing: $39-89/usuario/mes

---

## 6. [Próximo Competidor]

*Pendiente de análisis...*

---

## Matriz Comparativa General

| Feature | AURITY | NotaSalud | Telepatía | Leona | Itaca | Dorascribe |
|---------|--------|-----------|-----------|-------|-------|------------|
| Notas SOAP | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Transcripción audio | ✅ | ✅ | ✅ | ✅ (WA) | ✅ | ✅ |
| Recetas | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| IA aprende estilo | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Templates especialidad | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Templates personalizables | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Multi-idioma | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ (4) |
| Plan gratuito | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (20/mes) |
| App móvil | PWA | 🔜 | ✅ | ✅ | ✅ | ✅ |
| Integración EHR | ❌ | ❌ | ✅ | ❌ | ✅ | ⚠️ |
| Cumplimiento HIPAA | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ |
| Auditoría inmutable | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| White label on-prem | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Roadmap de Features Sugerido

### Fase 1 - Quick Wins
- [ ] Generación de recetas médicas
- [ ] Métricas de ahorro de tiempo por médico
- [ ] Traducción automática de términos médicos
- [ ] Mensajes programados (recordatorios de citas)
- [ ] **Auto-completado para entradas repetitivas**

### Fase 2 - Mejoras UX
- [ ] **Templates por especialidad** (psiquiatría, pediatría, cirugía, etc.)
- [ ] **Plantillas personalizables** (usuario edita campos/secciones)
- [ ] IA que aprende estilo del médico
- [ ] Flujo de aprobación de notas (revisar antes de guardar)
- [ ] Respuestas sugeridas para preguntas frecuentes
- [ ] **Citas/fuentes en respuestas de IA**

### Fase 3 - Integraciones
- [ ] **Integración videollamadas (Zoom/Meet/Teams)**
- [ ] Integración con sistemas EHR (HL7 FHIR)
- [ ] App móvil nativa (iOS/Android)
- [ ] Integración WhatsApp Business API

### Fase 4 - Modelo de Negocio
- [ ] **Plan freemium** (20 sesiones/mes gratis)
- [ ] Pricing tiers ($39-89/usuario/mes referencia)

---

## Referencia de Precios del Mercado

| Competidor | Plan Básico | Plan Pro | Notas |
|------------|-------------|----------|-------|
| Dorascribe | $39/mes | $89/mes | 20 gratis/mes |
| NotaSalud | N/D | N/D | - |
| Telepatía | N/D | N/D | - |
| Leona | N/D | N/D | - |
| Itaca | N/D | N/D | - |

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2025-11-21 | Análisis inicial: NotaSalud |
| 2025-11-21 | Agregado: Telepatía AI |
| 2025-11-21 | Agregado: Leona Health (enfoque WhatsApp) |
| 2025-11-21 | Agregado: Itaca AI (líder LATAM, 20k+ usuarios) |
| 2025-11-21 | Agregado: Dorascribe (precios públicos, freemium) |

