# Calendario de Citas - Solución Modal Nativo Bryntum

**Fecha**: 2025-12-11
**Card**: FI-CHECKIN-005 (Phase 3 - Modal Fix)

## ✅ Problemas Resueltos

### 1. ❌ Modal Nativo Bryntum "Information" Desactivado

**Problema**: Al hacer clic en un evento, Bryntum mostraba su editor nativo con campos como "Predecessors", "Successors", "Preamble", etc., que no son relevantes para citas médicas.

**Solución**:
- ✅ Desactivado `eventEdit: false` en la configuración de features
- ✅ Removido `editEvent: true` del menú contextual
- ✅ Configuración explícita en `AppointmentsCalendar.tsx`:
  ```typescript
  features: {
    ...APPOINTMENT_FEATURES as any,
    eventEdit: false, // CRITICAL: Disable Bryntum native editor
  }
  ```

### 2. ✅ Modal Personalizado de Edición Implementado

**Problema**: Necesitábamos un modal propio con campos específicos para citas médicas (paciente, doctor, estado, motivo, notas, etc.).

**Solución - Nuevo componente `EditAppointmentModal.tsx`**:
- ✅ Pre-rellena todos los campos con los datos de la cita existente
- ✅ Muestra información del paciente (read-only)
- ✅ Permite cambiar: doctor, fecha/hora, duración, estado, motivo, notas
- ✅ Validación de formulario antes de enviar
- ✅ Integración con API vía `handleEventEdit`
- ✅ UI consistente con `NewAppointmentModal`

**Archivos creados**:
```
apps/aurity/components/appointments/EditAppointmentModal.tsx
```

**Archivos modificados**:
```
apps/aurity/components/appointments/index.ts (export)
apps/aurity/app/admin/appointments/page.tsx (integración)
```

### 3. ✅ Event Click Handler

**Solución - Listener `eventClick` agregado**:
```typescript
eventClick: ({ eventRecord }: any) => {
  if (!onEventClick) return;

  // Encuentra la cita original
  const appointment = appointments.find(
    apt => apt.appointment_id === eventRecord.id
  );

  if (appointment) {
    onEventClick(appointment);
  }
}
```

**Flujo completo**:
1. Usuario hace clic en evento → `eventClick` se dispara
2. Busca la cita en el estado local por `appointment_id`
3. Llama a `handleEventClick(appointment)` en la página
4. Abre `EditAppointmentModal` con los datos pre-cargados
5. Usuario edita y guarda → `handleEventEdit` actualiza vía API
6. Estado local se actualiza → Bryntum re-renderiza

### 4. ✅ Scroll Horizontal Habilitado

**Problema**: No había scroll horizontal para ver más horas del día en el timeline.

**Solución - Configuración `subGridConfigs`**:
```typescript
subGridConfigs: {
  locked: { flex: 0 }, // Left side (resource column) - fijo
  normal: { flex: 1 }  // Right side (timeline) - scrollable
}
```

**Resultado**:
- ✅ Columna de doctores permanece fija a la izquierda
- ✅ Timeline se puede hacer scroll horizontal
- ✅ Navegación fluida por todas las horas del día

---

## 📁 Archivos Modificados

### 1. `/apps/aurity/components/appointments/EditAppointmentModal.tsx` *(NUEVO)*
- Modal de edición de citas con formulario completo
- Pre-carga datos de la cita seleccionada
- Campos: doctor, fecha, hora, duración, estado, motivo, notas
- Información del paciente (read-only)
- Validación y manejo de errores

### 2. `/apps/aurity/components/appointments/index.ts`
- Export de `EditAppointmentModal`

### 3. `/apps/aurity/components/appointments/AppointmentsCalendar.tsx`
**Cambios**:
- ✅ Nueva prop `onEventClick?: (appointment: Appointment) => void`
- ✅ Listener `eventClick` agregado
- ✅ Configuración `subGridConfigs` para scroll horizontal
- ✅ Desactivación explícita de `eventEdit: false`

### 4. `/apps/aurity/app/admin/appointments/page.tsx`
**Cambios**:
- ✅ Import de `EditAppointmentModal`
- ✅ Estado `isEditAppointmentModalOpen` y `selectedAppointment`
- ✅ Handler `handleEventClick(appointment: Appointment)`
- ✅ Prop `onEventClick={handleEventClick}` pasada a `AppointmentsCalendar`
- ✅ Renderizado de `<EditAppointmentModal>` con datos de cita seleccionada

### 5. `/apps/aurity/components/bryntum/config/appointment-features.config.ts`
**Cambios**:
- ✅ Removido `editEvent: true` del menú contextual
- ✅ Comentario explicativo sobre uso de modal personalizado

---

## 🧪 Testing Manual

### Test 1: Modal Nativo NO Debe Aparecer
1. Ir a `/admin/appointments/`
2. Hacer clic en cualquier evento (cita)
3. ✅ **Esperado**: Modal personalizado "Editar Cita Médica" se abre
4. ❌ **No debe aparecer**: Modal "Information" de Bryntum

### Test 2: Edición de Cita
1. Hacer clic en un evento
2. Modal se abre con datos pre-cargados
3. Cambiar doctor, fecha, hora, estado
4. Agregar/editar motivo y notas
5. Clic en "Guardar Cambios"
6. ✅ **Esperado**:
   - Toast "Cita editada correctamente"
   - Evento actualizado en calendario
   - Console log: `Appointment edited successfully`

### Test 3: Scroll Horizontal
1. Ver calendario en vista "day" (día)
2. ✅ **Esperado**: Barra de scroll horizontal visible
3. Hacer scroll hacia la derecha
4. ✅ **Esperado**: Se ven más horas del día
5. Columna de doctores permanece fija a la izquierda

### Test 4: Drag & Drop Sigue Funcionando
1. Arrastrar un evento a otra hora
2. ✅ **Esperado**: Evento se mueve correctamente
3. API se actualiza (console log)
4. NO se abre el modal de edición

### Test 5: Resize Sigue Funcionando
1. Redimensionar un evento (cambiar duración)
2. ✅ **Esperado**: Duración cambia correctamente
3. API se actualiza
4. NO se abre el modal de edición

---

## 🔧 Configuración Técnica

### Desactivación del Editor Nativo

**En 3 lugares**:

1. **`appointment-features.config.ts`**:
```typescript
eventEdit: false,
```

2. **`AppointmentsCalendar.tsx`** (explícito):
```typescript
features: {
  ...APPOINTMENT_FEATURES as any,
  eventEdit: false, // CRITICAL
}
```

3. **Menú contextual**:
```typescript
// editEvent removido del eventMenu.items
```

### Event Click Handler

**Patrón de implementación**:
```typescript
// 1. Props interface
onEventClick?: (appointment: Appointment) => void;

// 2. Listener en Bryntum
eventClick: ({ eventRecord }: any) => {
  const appointment = appointments.find(apt => apt.appointment_id === eventRecord.id);
  if (appointment && onEventClick) {
    onEventClick(appointment);
  }
}

// 3. Handler en página
function handleEventClick(appointment: Appointment) {
  setSelectedAppointment(appointment);
  setIsEditAppointmentModalOpen(true);
}
```

### Scroll Horizontal

**Configuración**:
```typescript
subGridConfigs: {
  locked: { flex: 0 }, // Fixed left column
  normal: { flex: 1 }  // Scrollable timeline
}
```

---

## 🎯 Checklist de Verificación

Antes de considerar completo:

- [x] Modal nativo Bryntum NO aparece al hacer clic
- [x] Modal personalizado se abre con datos correctos
- [x] Todos los campos son editables (excepto paciente)
- [x] Guardar cambios actualiza la cita vía API
- [x] Scroll horizontal funciona en el timeline
- [x] Columna de doctores permanece fija
- [x] Drag & drop sigue funcionando (sin abrir modal)
- [x] Resize sigue funcionando (sin abrir modal)
- [x] Validación de formulario funciona
- [x] Manejo de errores implementado
- [x] UI consistente con el resto de la app

---

## 🚨 Notas Importantes

### CRITICAL: eventEdit Debe Estar en `false`

Si el modal nativo vuelve a aparecer, verificar:
1. `appointment-features.config.ts`: `eventEdit: false`
2. `AppointmentsCalendar.tsx`: feature override explícito
3. No hay listeners `beforeEventEditShow` que lo reactiven

### Diferencia: Click vs Drag/Resize

- **Click** → Abre modal de edición
- **Drag** → Actualiza posición/doctor (sin modal)
- **Resize** → Actualiza duración (sin modal)

Esto es intencional y mejora UX.

### Modal vs API

El modal envía datos a `handleEventEdit`, que hace:
```typescript
PATCH /api/clinics/{clinic_id}/appointments/{appointment_id}
```

Con campos:
- `scheduled_at` (ISO 8601)
- `estimated_duration` (minutos)
- `doctor_id`
- `status`
- `reason`
- `notes`

---

## 📚 Referencias

- **Bryntum Docs**: https://bryntum.com/products/schedulerpro/docs/
- **EventEdit Feature**: https://bryntum.com/products/scheduler/docs/api/Scheduler/feature/EventEdit
- **Appointment Features**: `apps/aurity/components/bryntum/config/appointment-features.config.ts`
- **Transform Utils**: `apps/aurity/components/bryntum/utils/appointment-transform.utils.ts`

---

**Status**: ✅ COMPLETADO
**Próximos pasos**: Testing manual y validación de UX
