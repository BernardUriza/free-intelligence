# Bryntum Scheduler - Página de Demostración

## 📍 Acceso

**URL:** `http://localhost:9000/demos/bryntum`

Esta es una ruta oculta (no aparece en el menú de navegación) para debugging y validación.

## 🎯 Propósito

Página de pruebas para validar que Bryntum SchedulerPro renderiza correctamente:

- ✅ **Datos hardcodeados** (no depende de APIs)
- ✅ **Dos modos:** Timeline (memoria longitudinal) y Appointments (citas médicas)
- ✅ **Control total:** cambiar vista (día/semana/mes), navegar fechas, forzar refresh
- ✅ **Debug visible:** console logs, status indicators, refresh counter

## 🔧 Casos de Uso

### 1. Verificar que Bryntum funciona
Si el scheduler no renderiza en producción, usa esta página para aislar el problema:
- ¿Renderiza aquí pero no en `/timeline` o `/admin/appointments`? → Problema con datos de API
- ¿No renderiza ni aquí? → Problema con Bryntum loader o archivos JS/CSS

### 2. Debugging visual
- Abre DevTools (F12) → Console
- Busca logs con `[BryntumDemo]`
- Verifica que se cargan CSS y JS de Bryntum en Network tab

### 3. Probar cambios en config
Modifica `buildTimelineSchedulerConfig` o `buildAppointmentSchedulerConfig` y recarga la página para ver efecto inmediato.

## 📊 Datos Demo

### Timeline (8 eventos)
- 4 mensajes de chat (user/assistant)
- 4 transcripciones de audio
- Distribuidos en últimas 24 horas

### Appointments (4 citas)
- 3 doctores (Cardiología, Pediatría, Dermatología)
- 4 citas con diferentes estados (scheduled, confirmed, checked_in, in_progress)
- Distribuidas en próximas 8 horas

## 🚀 Próximos Pasos

Si esta demo funciona bien pero `/timeline` no:
1. Revisar API `/api/workflows/aurity/timeline/memory`
2. Verificar transformación de datos en `event-transform.utils.ts`
3. Comparar estructura de eventos demo vs. eventos reales

Si esta demo NO funciona:
1. Verificar que existan archivos:
   - `/public/css/bryntum/schedulerpro.classic-dark.css`
   - `/public/js/bryntum/schedulerpro.wc.module.js`
2. Revisar console para errores de carga
3. Verificar que `useBryntumScheduler` hook se ejecute correctamente

## 📝 Notas

- Esta ruta está marcada como `hidden: true` en `lib/navigation.ts`
- No requiere autenticación (útil para pruebas rápidas)
- Los eventos de drag & drop/resize muestran alerts (no se guardan)
