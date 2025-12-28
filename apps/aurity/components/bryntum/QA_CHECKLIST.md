# QA Checklist - Timeline Scheduler Refactorizado

**Fecha**: 8 de diciembre de 2025  
**Versión**: TimelineScheduler refactorizado (Bryntum modular)  
**Tester**: _____________  

---

## ✅ Pre-Checklist

- [ ] **Backup verificado**: `TimelineScheduler.backup.tsx` existe
- [ ] **Sin errores TypeScript**: `npm run type-check` pasa
- [ ] **Build exitoso**: `npm run build` completa sin errores
- [ ] **Dev server corriendo**: `npm run dev` en puerto 9000

---

## 1. 🚀 Inicialización

### Carga Inicial
- [ ] **Página carga** sin errores en consola
- [ ] **Scheduler renderiza** (visualización Bryntum visible)
- [ ] **Eventos aparecen** en timeline (si hay datos)
- [ ] **Loading spinner** se muestra durante carga inicial
- [ ] **Empty state** correcto cuando no hay eventos

### Recursos
- [ ] **Dos filas visibles**: "💬 Chat" y "🎙️ Audio"
- [ ] **Columna "Fuente"** en lado izquierdo (120px)
- [ ] **Eventos en fila correcta** (chat → chat row, audio → audio row)

---

## 2. 📅 Navegación de Fecha

### Controles de Navegación
- [ ] **Botón "Hoy"** lleva a fecha actual
- [ ] **Flecha izquierda** retrocede período correcto
- [ ] **Flecha derecha** avanza período correcto
- [ ] **Fecha mostrada** actualiza correctamente en toolbar

### Navegación por Teclado
- [ ] **`Shift + ←`** retrocede un período
- [ ] **`Shift + →`** avanza un período
- [ ] **`T`** regresa a fecha de hoy
- [ ] **Shortcuts no activan** en campos de texto (input/textarea)

### Botón "Último"
- [ ] **Visible** cuando hay eventos
- [ ] **Click** navega al evento más reciente
- [ ] **Time axis** se centra en evento latest

---

## 3. 🔍 Modos de Vista

### Selector de Vista (Day/Week/Month)
- [ ] **Día**: Muestra 24 horas (00:00 - 23:59)
- [ ] **Semana**: Muestra lunes a domingo (ISO 8601)
- [ ] **Mes**: Muestra todos los días del mes
- [ ] **Cambio de vista** preserva fecha de referencia
- [ ] **Ticks correctos** (Día: horas, Semana: días, Mes: días compactos)

### Headers
- [ ] **Día**: "lunes, 8 diciembre 2025" + horas
- [ ] **Semana**: "Semana W, MMMM YYYY" + días abreviados
- [ ] **Mes**: "MMMM YYYY" + números de día

---

## 4. 🔎 Zoom

### Controles de Zoom
- [ ] **Botón `-`** aleja (hasta 50%)
- [ ] **Botón `+`** acerca (hasta 200%)
- [ ] **Porcentaje** se muestra correctamente (50% - 200%)
- [ ] **Botones disabled** en límites (50% y 200%)
- [ ] **Tick width** cambia según zoom

### Teclado
- [ ] **`+` o `=`** aumenta zoom
- [ ] **`-`** reduce zoom

---

## 5. 🎯 Eventos

### Renderizado
- [ ] **Eventos visibles** como barras horizontales
- [ ] **Colores correctos**:
  - Chat usuario: Sky (#0ea5e9)
  - Chat asistente: Violet (#8b5cf6)
  - Transcripción: Emerald (#10b981)
- [ ] **Nombre truncado** (máx 50 chars + "...")
- [ ] **Posición horizontal** alineada con timestamp

### Tooltips
- [ ] **Hover sobre evento** muestra tooltip
- [ ] **Tooltip contiene**:
  - Tipo de evento (Usuario/Asistente/Transcripción)
  - Timestamp formateado
  - Preview de contenido (200 chars max)
  - Duración (si es audio)
- [ ] **Tooltip desaparece** al salir del evento

### Click en Evento
- [ ] **Click abre modal** de detalles
- [ ] **Modal muestra**:
  - Tipo y color
  - Timestamp completo (es-MX format)
  - Contenido completo (sin truncar)
  - Botón copiar contenido
  - Metadata footer (sesión, persona, confianza, idioma)
- [ ] **Botón X** cierra modal
- [ ] **Click fuera** cierra modal
- [ ] **`Esc`** cierra modal

---

## 6. 📂 Navigate Drawer

### Apertura/Cierre
- [ ] **Botón panel** toggle drawer
- [ ] **Icono cambia** (PanelLeftOpen ↔ PanelLeftClose)
- [ ] **Drawer 72px width** cuando abierto
- [ ] **`Esc`** cierra drawer (si modal no está abierto)

### Stats
- [ ] **Chat count** correcto (mensajes de chat)
- [ ] **Audio count** correcto (transcripciones)
- [ ] **Colores** sky (chat) y emerald (audio)

### Búsqueda de Sesiones
- [ ] **Input search** filtra sesiones
- [ ] **Lista actualiza** en tiempo real
- [ ] **Sin resultados** muestra "No hay sesiones"

### Selección de Sesión
- [ ] **"Todas las sesiones"** muestra todos los eventos
- [ ] **Sesión específica** filtra solo eventos de esa sesión
- [ ] **Sesión seleccionada** highlighted (emerald bg)
- [ ] **Counts actualizan** según filtro de sesión

---

## 7. 🎨 Leyenda de Eventos

### Visualización (Desktop)
- [ ] **Visible** en viewport md+ (≥768px)
- [ ] **Tres badges**:
  - Usuario (sky dot)
  - Asistente (violet dot)
  - Audio (emerald dot)
- [ ] **Hidden** en mobile (<768px)

---

## 8. ⌨️ Keyboard Shortcuts Bar

### Barra Inferior
- [ ] **Visible** en bottom de scheduler
- [ ] **Muestra shortcuts**:
  - `Shift + ←/→` Navegar
  - `+/-` Zoom
  - `T` Hoy
  - `Esc` Cerrar
- [ ] **`<kbd>` tags** styled correctamente

---

## 9. 🔄 Actualizaciones en Tiempo Real

### Cambio de Eventos (Props)
- [ ] **Nuevos eventos** aparecen automáticamente
- [ ] **Event store** actualiza sin re-render completo
- [ ] **Scroll position** preservada
- [ ] **Selected session** preservada después de update

---

## 10. 🚨 Error Handling

### Casos de Error
- [ ] **Bryntum no carga**: Mensaje de error en consola
- [ ] **Container ref null**: No crash, scheduler no renderiza
- [ ] **Eventos vacíos**: Empty state visible
- [ ] **isLoading true**: Loading spinner visible

---

## 11. 📱 Responsive

### Mobile (<768px)
- [ ] **Toolbar adapta**: Labels ocultos, solo iconos
- [ ] **Drawer 100% width** cuando abierto (overlay)
- [ ] **Leyenda oculta** (solo en desktop)
- [ ] **Scheduler usable** en touch devices

### Tablet (768px - 1024px)
- [ ] **View mode labels** visibles
- [ ] **Zoom controls** funcionales
- [ ] **Drawer side-by-side** con scheduler

---

## 12. 🎭 Integración con Hook

### useLongitudinalMemory
- [ ] **Events** pasan correctamente al scheduler
- [ ] **chatCount/audioCount** sincronizados con drawer
- [ ] **isLoading** controla loading overlay
- [ ] **Infinite scroll** compatible con scheduler

---

## 13. 🧪 Edge Cases

### Datos Extremos
- [ ] **0 eventos**: Empty state visible
- [ ] **1000+ eventos**: Performance aceptable (<2s render)
- [ ] **Eventos simultáneos**: No overlap visual (barMargin: 4)
- [ ] **Evento muy corto** (1s): Mínimo width visible

### Timestamps
- [ ] **Eventos futuros**: Posicionados correctamente
- [ ] **Eventos pasados** (años atrás): Navegación funcional
- [ ] **Cambio de timezone**: Timestamps correctos

---

## 14. ✅ Sign-Off

### Resultado Final
- [ ] **Sin errores** en consola del navegador
- [ ] **Sin warnings** TypeScript
- [ ] **Performance** aceptable (60fps scroll)
- [ ] **UX fluida**: Transiciones suaves, no glitches

### Browsers Testeados
- [ ] Chrome/Edge (últimas 2 versiones)
- [ ] Firefox (últimas 2 versiones)
- [ ] Safari (macOS/iOS)

---

## 📝 Notas de QA

**Issues encontrados**:
```
1. 
2. 
3. 
```

**Observaciones**:
```
- 
- 
```

**Recomendaciones**:
```
- 
- 
```

---

**Tester**: _____________  
**Fecha**: ___/___/2025  
**Aprobado**: ☐ Sí  ☐ No  
**Comentarios**: _______________________________________________
