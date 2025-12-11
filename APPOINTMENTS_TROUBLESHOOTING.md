# Troubleshooting - Agenda de Citas

**Fecha**: 2025-12-11
**Sistema**: AURITY - Free Intelligence
**Componente**: AppointmentsCalendar

## Problemas Comunes y Soluciones

### 1. Calendario No Se Muestra (Pantalla en Blanco)

**Síntomas:**
- Spinner de carga infinito
- Contenedor vacío donde debería estar el calendario
- Errores en consola sobre Bryntum

**Causas Posibles:**
- Archivos de Bryntum no encontrados (`/js/bryntum/schedulerpro.wc.module.js`)
- CSS de Bryntum no cargado (`/css/bryntum/schedulerpro.classic-dark.css`)
- Error en inicialización por React Strict Mode

**Soluciones:**

```bash
# 1. Verificar que existan los archivos de Bryntum
ls -la apps/aurity/public/js/bryntum/schedulerpro.wc.module.js
ls -la apps/aurity/public/css/bryntum/schedulerpro.classic-dark.css

# 2. Si no existen, copiar desde el paquete instalado
mkdir -p apps/aurity/public/js/bryntum
mkdir -p apps/aurity/public/css/bryntum
cp node_modules/@bryntum/schedulerpro/schedulerpro.wc.module.js apps/aurity/public/js/bryntum/
cp node_modules/@bryntum/schedulerpro/schedulerpro.classic-dark.css apps/aurity/public/css/bryntum/

# 3. Reiniciar el servidor de desarrollo
cd apps/aurity && pnpm dev
```

---

### 2. Citas No Se Cargan (Doctores Visibles, Sin Citas)

**Síntomas:**
- Los doctores aparecen en la columna izquierda
- No hay bloques de citas en el calendario
- API retorna datos pero no se visualizan

**Causas Posibles:**
- Formato de fecha incorrecto en el backend
- Filtro de fecha demasiado restrictivo
- Problema en la transformación de datos

**Verificación:**

```bash
# Probar el endpoint directamente
curl -X GET "http://localhost:7001/api/clinics/{clinic_id}/appointments?date=2025-12-11" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Solución en Backend:**

El problema puede estar en el filtro de fecha. Verificar en `backend/api/public/clinics.py`:

```python
# ACTUAL (puede ser muy restrictivo)
if date:
    filter_date = datetime.fromisoformat(date).date()
    query = query.filter(
        Appointment.scheduled_at >= datetime.combine(filter_date, datetime.min.time()),
        Appointment.scheduled_at < datetime.combine(filter_date, datetime.min.time()) + timedelta(days=1),
    )

# MEJORADO - Asegurarse de comparar correctamente
if date:
    try:
        filter_date = datetime.fromisoformat(date).date()
        start_of_day = datetime.combine(filter_date, datetime.min.time(), tzinfo=UTC)
        end_of_day = start_of_day + timedelta(days=1)
        query = query.filter(
            Appointment.scheduled_at >= start_of_day,
            Appointment.scheduled_at < end_of_day,
        )
    except ValueError as e:
        logger.warning(f"Invalid date format: {date}", error=str(e))
```

---

### 3. Drag & Drop No Funciona

**Síntomas:**
- No se puede arrastrar citas
- Citas se revierten después de arrastrarlas
- Error en consola del navegador

**Causas Posibles:**
- `onEventDrop` no está definido en el componente padre
- Error en la llamada API de actualización
- Permisos de CORS

**Solución:**

Verificar que el handler esté correctamente implementado en `page.tsx`:

```typescript
async function handleEventDrop(eventData: {
  appointment_id: string;
  scheduled_at: string;
  doctor_id: string;
}) {
  if (!selectedClinic) return;

  try {
    const response = await fetch(
      `${API_BASE}/api/clinics/${selectedClinic}/appointments/${eventData.appointment_id}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAccessToken()}` // ← ASEGÚRATE DE INCLUIR TOKEN
        },
        body: JSON.stringify({
          scheduled_at: eventData.scheduled_at,
          doctor_id: eventData.doctor_id,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update appointment");
    }

    const updated = await response.json();

    // Update local state
    setAppointments((prev) =>
      prev.map((apt) =>
        apt.appointment_id === updated.appointment_id ? updated : apt
      )
    );

    toastSuccess("Cita actualizada correctamente");
  } catch (error) {
    console.error("Failed to update appointment:", error);
    await fetchAppointments(selectedClinic, currentDate);
    toastError(error instanceof Error ? error.message : "Error al actualizar cita");
  }
}
```

---

### 4. Problema de Timezone (Citas Aparecen en Hora Incorrecta)

**Síntomas:**
- Citas aparecen algunas horas antes/después
- Diferencia constante en todas las citas

**Causa:**
- Backend devuelve UTC, frontend interpreta como hora local

**Solución:**

En `appointment-transform.utils.ts`, asegurarse de parsear correctamente:

```typescript
export function transformAppointment(appointment: Appointment): BryntumEvent {
  // CORREGIR: Parsear como UTC explícitamente
  const startDate = new Date(appointment.scheduled_at);

  // Si el backend NO incluye 'Z' o '+00:00', agregar:
  // const startDate = new Date(appointment.scheduled_at + 'Z');

  const endDate = new Date(
    startDate.getTime() + appointment.estimated_duration * 60000
  );

  return {
    id: appointment.appointment_id,
    resourceId: appointment.doctor_id,
    startDate,
    endDate,
    // ... resto de campos
  };
}
```

---

### 5. Citas Duplicadas Después de Actualizar

**Síntomas:**
- Aparecen 2 copias de la misma cita después de drag & drop
- Las citas se multiplican al cambiar de vista

**Causa:**
- Problema en el update del estado local
- Bryntum no destruye correctamente instancias previas

**Solución:**

En `AppointmentsCalendar.tsx`, mejorar el cleanup:

```typescript
useEffect(() => {
  if (!schedulerRef.current) return;

  const instance = schedulerRef.current;

  // MEJORAR: Usar removeAll() antes de agregar nuevos datos
  if (instance.eventStore) {
    instance.eventStore.removeAll();
    instance.eventStore.data = transformAppointments(appointments);
  }
}, [appointments]);
```

---

### 6. Performance - Calendario Se Congela

**Síntomas:**
- Lag al cambiar de fecha
- Navegación lenta entre vistas
- Alto uso de CPU

**Soluciones:**

```typescript
// 1. Limitar cantidad de citas cargadas
async function fetchAppointments(clinicId: string, date: Date) {
  const dateStr = date.toISOString().split("T")[0];

  // MEJORA: Agregar límite
  const res = await fetch(
    `${API_BASE}/api/clinics/${clinicId}/appointments?date=${dateStr}&limit=100`
  );

  // ...
}

// 2. Debounce en navegación
import { debounce } from 'lodash';

const debouncedFetch = debounce((clinic: string, date: Date) => {
  fetchAppointments(clinic, date);
}, 300);

function navigateDate(direction: "prev" | "next") {
  const newDate = new Date(currentDate);
  // ... calcular nueva fecha
  setCurrentDate(newDate);
  debouncedFetch(selectedClinic, newDate);
}
```

---

## Checklist de Diagnóstico

Ejecuta estos pasos para identificar el problema:

```bash
# 1. Verificar backend está corriendo
curl http://localhost:7001/health

# 2. Verificar endpoint de clínicas
curl http://localhost:7001/api/clinics

# 3. Verificar endpoint de doctores (reemplazar {clinic_id})
curl http://localhost:7001/api/clinics/{clinic_id}/doctors

# 4. Verificar endpoint de citas
curl "http://localhost:7001/api/clinics/{clinic_id}/appointments?date=2025-12-11"

# 5. Ver logs del backend
tail -f data/logs/backend.log

# 6. Ver errores de consola en navegador
# Abrir DevTools (F12) → Pestaña Console

# 7. Ver errores de red
# DevTools → Network → Filtrar por "appointments"
```

## Log de Errores Comunes

### Error: "Failed to fetch"
```
Causa: CORS o backend no responde
Solución: Verificar NEXT_PUBLIC_API_BASE en .env.local
```

### Error: "Cannot read property 'data' of undefined"
```
Causa: schedulerRef.current es null
Solución: Esperar inicialización completa antes de actualizar
```

### Error: "TypeError: Cannot add property resourceId"
```
Causa: Objeto inmutable pasado a Bryntum
Solución: Usar spread operator {...appointment}
```

### Error: 401 Unauthorized
```
Causa: Token de Auth0 no incluido en headers
Solución: Agregar Authorization header con Bearer token
```

---

## Contacto y Soporte

Si el problema persiste después de seguir estos pasos:

1. Revisar logs detallados en `data/logs/`
2. Verificar versiones de paquetes: `pnpm list @bryntum/schedulerpro`
3. Consultar documentación de Bryntum: https://bryntum.com/products/schedulerpro/docs/
4. Revisar issues conocidos en el repositorio

**Autor**: Bernard Uriza Orozco
**Última actualización**: 2025-12-11
