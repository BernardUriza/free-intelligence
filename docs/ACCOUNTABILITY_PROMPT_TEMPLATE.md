# Prompt Template: Sistema de Accountability para Proyectos

**Versión**: 1.0
**Autor**: Bernard Uriza Orozco
**Uso**: Copiar y adaptar para cualquier proyecto que requiera disciplina extrema

---

## 🎯 Prompt Genérico (Copy-Paste)

```markdown
Crea un SISTEMA DE ACCOUNTABILITY para [NOMBRE_PROYECTO].

No solo un plan. Es un contrato de vida o muerte para [NOMBRE_PROYECTO].

## Contexto del Proyecto

- **Nombre**: [NOMBRE_PROYECTO]
- **Objetivo**: [DESCRIPCIÓN_1_LÍNEA]
- **Duración sprint**: [X] días
- **Compromiso diario**: [Y] horas/día
- **Descansos**: [SÍ/NO] (si NO, especificar "SIN DESCANSO")

## Sprint Anterior (Análisis de Velocidad)

**Si existe sprint previo, proporcionar**:

| Task | Estimado | Real | Factor |
|------|----------|------|--------|
| [TASK-001] | Xh | Yh | Z |
| [TASK-002] | Xh | Yh | Z |
| **Total** | **Xh** | **Yh** | **Z** |

**Velocity Factor**: [FACTOR] (ej: 0.07 = tareas toman 7% del tiempo estimado)

**Si NO existe sprint previo**:
- Usar factor conservador: 0.5 (tareas toman 50% del tiempo estimado)
- Ajustar después del primer sprint

## Capacidad del Sprint

- **Tiempo disponible**: [X días] × [Y horas/día] = [Z horas totales]
- **Con velocity factor [F]**: Z horas reales ≈ [Z/F] horas estimadas
- **Estrategia**: Seleccionar [A-B] horas estimadas para buffer

## Tarjetas/Features Seleccionadas

**Lista de tareas con prioridad**:

1. [TASK-ID] - [Descripción] [Estimado: Xh, Prioridad: P0/P1]
2. [TASK-ID] - [Descripción] [Estimado: Xh, Prioridad: P0/P1]
...
N. [TASK-ID] - [Descripción] [Estimado: Xh, Prioridad: P0/P1]

**Total estimado**: [X] horas → [Y] horas reales (con velocity [F])

## Outcomes Esperados

Al final del sprint, el proyecto tendrá:

1. [OUTCOME_1] (ej: Feature X implementada)
2. [OUTCOME_2] (ej: Tests pasando 100%)
3. [OUTCOME_3] (ej: Documentación actualizada)
...

## Requerimientos del Sistema de Accountability

Genera los siguientes archivos/secciones:

### 1. Plan del Sprint (SPRINT_[N]_PLAN.md)

Debe incluir:
- Análisis de velocidad (si existe sprint previo)
- Capacidad y estimación
- Selección de tarjetas con RICE o priorización
- Roadmap día a día
- **Sección de Accountability** con:
  - Compromiso inquebrantable (contrato formal)
  - Reglas de disciplina ([Y]h/día sin excepción)
  - Daily tracking obligatorio
  - Bloqueo de excusas comunes
  - Red flags (alertas de abandono)
  - Consecuencias de incumplimiento (brutalmente honestas)
  - Estrategia anti-procrastinación
  - Contrato con firma

### 2. Tracker Diario (SPRINT_[N]_TRACKER.md)

Debe incluir:
- Dashboard de métricas (días, horas, tasks, commits)
- Log diario con template:
  - ⏰ Inicio: __:__
  - ⏰ Fin: __:__
  - ⏱️ Horas: __/[Y]h
  - ✅ Completado: [ ]
  - 📝 Progreso:
  - 🔗 Commit:
  - 💭 Notas:
  - 🚩 Bloqueos:
- Sección de red flags
- Reflexiones finales del sprint

### 3. Reglas de Disciplina

Incluir:
- [Y] horas diarias, [X] días [consecutivos/con descanso]
- Daily tracking: [Sistema de tracking] + commits + bitácora
- Checkpoint: inicio y fin de sesión
- Red flags:
  - 🚨 2 días sin commit → Alerta roja
  - 🚨 3 días sin progreso → Peligro crítico
  - 🚨 5 días sin actividad → Sprint fallido

### 4. Consecuencias de Incumplimiento

**Si NO se completa el sprint**:

1. **Reconocimiento brutal**:
   - [PROYECTO] no era prioritario
   - La idea importaba más que la ejecución
   - El proyecto era [masturbación intelectual/hobby/fantasía], no [ingeniería/negocio/realidad]

2. **Acción correctiva**:
   - OPCIÓN A: Cerrar el proyecto definitivamente
   - OPCIÓN B: Replantear con compromiso real y recursos dedicados
   - NO existe OPCIÓN C (continuar sin cambios)

3. **Deuda técnica emocional**:
   - Reconocer que abandonaste por falta de disciplina
   - Documentar el "por qué" en bitácora
   - Decidir conscientemente si esto es o no para ti

### 5. Estrategia Anti-Procrastinación

Incluir:
- Técnica Pomodoro modificada (25 min obligatorios)
- Micro-wins (hacer ALGO > hacer nada)
- Ritual de inicio (2 minutos, sin excusas)
- Regla de los 2 minutos (si toma <2min, hazlo YA)

### 6. Contrato Formal

Incluir checkbox para:
- [ ] [Y]h diarias x [X] días
- [ ] [N] tasks completadas
- [ ] Commit diario
- [ ] Actualizar tracking diario
- [ ] Si fallo [Z] días, cerrar o replantear proyecto

**Firma**: _________________________
**Fecha**: [FECHA]

**Testigo**: [SISTEMA_IA] (este documento es evidencia)

## Estilo y Tono

- **Brutalmente honesto**: Sin azúcar, sin motivación falsa
- **Confrontacional**: El objetivo es que me cuestione si realmente quiero esto
- **Accionable**: Pasos claros, no filosofía
- **Medible**: Métricas concretas, no abstracciones
- **Sin escape**: Bloquear todas las excusas comunes

## Outputs Esperados

1. Archivo SPRINT_[N]_PLAN.md con sección de Accountability
2. Archivo SPRINT_[N]_TRACKER.md con templates diarios
3. Actualización a archivo principal del proyecto (ej: README, CLAUDE.md) con warning de compromiso

---

**Ejemplo de uso**:

"Crea un SISTEMA DE ACCOUNTABILITY para mi Portfolio Personal.
- 30 días, 2h/día, SIN DESCANSO
- No hay sprint previo, usar velocity 0.5
- 10 proyectos a completar
- Outcomes: Portfolio live, 5 case studies documentados"
```

---

## 🎯 Variaciones del Prompt

### Para proyectos cortos (1 semana)

```markdown
Crea un SISTEMA DE ACCOUNTABILITY para [PROYECTO] - SPRINT RÁPIDO.
- Duración: 7 días
- Compromiso: 4h/día, SIN DESCANSO
- Velocity: [si existe] o 0.5 [si nuevo]
- Tasks: [listar 3-5 tasks]
- Outcomes: [listar outcomes esperados]
- Red flags: 1 día sin commit = alerta, 2 días = crítico
```

### Para proyectos largos (3 meses)

```markdown
Crea un SISTEMA DE ACCOUNTABILITY para [PROYECTO] - SPRINT MARATHON.
- Duración: 90 días (3 sprints de 30 días)
- Compromiso: Xh/día, 1 día descanso/semana
- Velocity: [si existe] o 0.5 [si nuevo]
- Milestones: [listar milestones mensuales]
- Checkpoints semanales obligatorios
- Red flags: 3 días sin commit = alerta, 5 días = crítico
```

### Para hábitos personales (no coding)

```markdown
Crea un SISTEMA DE ACCOUNTABILITY para [HÁBITO].
- Ejemplos: Gym, Meditación, Escritura, Lectura
- Duración: [X] días
- Compromiso: [Y] minutos/día o [Z] veces/semana
- Métrica: [métrica específica, ej: 30 min gym, 1000 palabras, etc]
- Tracking: App/Journal/Spreadsheet
- Red flags: 2 días sin registro = alerta
```

---

## 📋 Checklist de Adaptación

Cuando uses este prompt para un nuevo proyecto:

- [ ] Reemplazar [NOMBRE_PROYECTO]
- [ ] Definir duración (días)
- [ ] Definir compromiso diario (horas)
- [ ] Especificar si hay descansos
- [ ] Calcular/estimar velocity factor
- [ ] Listar tasks con estimaciones
- [ ] Definir outcomes claros
- [ ] Ajustar red flags según duración
- [ ] Personalizar consecuencias (brutal pero relevante)
- [ ] Definir sistema de tracking (git, Trello, Notion, etc)

---

## 🔥 Filosofía del Sistema

**Este sistema NO es para**:
- Motivarte
- Hacerte sentir bien
- Darte palmaditas en la espalda
- Justificar excusas

**Este sistema ES para**:
- Confrontarte con la verdad
- Medir tu compromiso real
- Detectar auto-engaño temprano
- Forzar decisión: ejecutar o abandonar (no existe "intentar")

---

## 💡 Casos de Uso

### Coding Projects
```
Crea un SISTEMA DE ACCOUNTABILITY para mi API REST en Go.
- 15 días, 3h/día, SIN DESCANSO
- Velocity: 0.15 (basado en proyecto anterior)
- 8 endpoints a implementar
```

### Learning Projects
```
Crea un SISTEMA DE ACCOUNTABILITY para aprender Rust.
- 30 días, 2h/día, 1 día descanso/semana
- No hay velocity, usar 0.5
- 12 ejercicios de Rustlings + 1 proyecto personal
```

### Business Projects
```
Crea un SISTEMA DE ACCOUNTABILITY para lanzar mi SaaS MVP.
- 60 días, 4h/día, SIN DESCANSO
- Velocity: 0.08 (basado en sprint anterior)
- 15 features core + landing page + payment
```

### Personal Habits
```
Crea un SISTEMA DE ACCOUNTABILITY para escribir un libro.
- 90 días, 1h/día escritura, descanso domingos
- Métrica: 500 palabras/día mínimo
- Outcome: 45,000 palabras = primer draft completo
```

---

## 🚀 Prompt de Activación Rápida

**Versión ultra-corta para copiar-pegar**:

```
Sistema de accountability para [PROYECTO]. [X]días × [Y]h/día, [descansos?].
Velocity [Z si existe, 0.5 si nuevo]. [N] tasks. Brutal, medible, sin excusas.
```

**Ejemplo**:
```
Sistema de accountability para Free Intelligence Sprint 2. 15días × 4h/día, SIN DESCANSO.
Velocity 0.07. 12 tasks. Brutal, medible, sin excusas.
```

---

## 📝 Metadata del Template

**Versión**: 1.0
**Fecha de creación**: 2025-10-25
**Probado en**: Free Intelligence Sprint 2
**Resultado**: [Pendiente - completar después del sprint]
**Actualizaciones**: Agregar learnings después de Sprint 2

---

## 🎓 Learnings (Actualizar post-sprint)

**Después de cada uso del template, documentar**:

### Sprint N - [Proyecto]
- **Completado**: [SÍ/NO]
- **% de adherencia**: [X]%
- **Red flags activados**: [cuáles y cuándo]
- **Ajustes necesarios**: [qué cambiar para próxima vez]
- **Lección clave**: [1 línea brutal de verdad]

---

**Última actualización**: 2025-10-25
**Mantenedor**: Bernard Uriza Orozco
**Licencia**: Uso personal (adaptar libremente)
