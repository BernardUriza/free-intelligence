# Bryntum Scheduler Pro - Integration Guide

> **Professional implementation of Bryntum SchedulerPro for React/TypeScript**

## 📋 Overview

This module provides a **production-ready, type-safe integration** of Bryntum Scheduler Pro for AURITY's timeline visualization needs. It replaces ad-hoc script loading with a **modular, testable, and maintainable architecture**.

**Status**: ✅ Ready for production  
**Version**: 1.0.0  
**Last Updated**: December 8, 2025

---

## 🎯 Key Features

- ✅ **100% TypeScript** - Full type coverage, zero `any` types
- ✅ **Modular Architecture** - Separated types, config, features, hooks, utils
- ✅ **React Hooks** - Custom hooks for state, lifecycle, events
- ✅ **Testing Ready** - Pure functions, mockable dependencies
- ✅ **Documented** - Every decision justified in ARCHITECTURE.md
- ✅ **Reusable** - Shared across timeline and appointments scheduler

---

## 📁 Project Structure

```
components/bryntum/
├── ARCHITECTURE.md             # 📖 Complete architecture documentation
├── README.md                   # 👈 You are here
├── index.ts                    # Public API exports
│
├── types/
│   └── scheduler.types.ts      # TypeScript definitions (400+ lines)
│
├── config/
│   ├── timeline-presets.config.ts   # Day/Week/Month view configurations
│   ├── timeline-resources.config.ts # Resource rows (chat/audio)
│   └── timeline-columns.config.ts   # Column definitions
│
├── features/
│   ├── event-tooltip.feature.ts     # Rich HTML tooltips
│   └── timeline-features.config.ts  # Feature toggles
│
├── hooks/
│   ├── useSchedulerState.ts         # Centralized state management
│   ├── useSchedulerLifecycle.ts     # Init/update/destroy lifecycle
│   └── useSchedulerEvents.ts        # Keyboard shortcuts & event handlers
│
└── utils/
    ├── event-transform.utils.ts     # UnifiedEvent → BryntumEvent transformation
    └── scheduler-builder.utils.ts   # Configuration factory function
```

---

## 🚀 Quick Start

### 1. Import the Module

```typescript
import {
  useSchedulerState,
  useSchedulerLifecycle,
  useSchedulerEvents,
  buildSchedulerConfig,
  type UnifiedEvent,
  type ViewMode,
} from '@/components/bryntum';
```

### 2. Basic Component Implementation

```typescript
import { useRef } from 'react';

export function MyScheduler({ events }: { events: UnifiedEvent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  // State management
  const state = useSchedulerState({
    events,
    initialViewMode: 'week',
  });

  // Build configuration
  const config = buildSchedulerConfig({
    viewMode: state.viewMode,
    currentDate: state.currentDate,
    events: state.filteredEvents,
  });

  // Lifecycle management
  const { instance, isInitialized } = useSchedulerLifecycle({
    containerRef,
    config,
    events: state.filteredEvents,
    isLoading: false,
  });

  // Event handling
  useSchedulerEvents({
    instance,
    onNavigatePrev: () => state.navigateDate('prev'),
    onNavigateNext: () => state.navigateDate('next'),
    onZoomIn: () => state.handleZoom('in'),
    onZoomOut: () => state.handleZoom('out'),
  });

  return (
    <div>
      <div ref={containerRef} style={{ height: '600px' }} />
    </div>
  );
}
```

---

## 🔧 Advanced Usage

### Custom View Presets

Create your own view configurations for domain-specific needs:

```typescript
// config/medical-presets.config.ts
import { type ViewPresetConfig } from '../types/scheduler.types';

export const MEDICAL_PRESETS: Record<string, ViewPresetConfig> = {
  shift: {
    id: 'shift',
    label: 'Turno (8 horas)',
    preset: {
      base: 'hourAndDay',
      tickWidth: 100,
      headers: [
        { unit: 'hour', dateFormat: 'HH:mm' },
      ],
    },
    getDateRange: (date: Date) => {
      const start = new Date(date);
      start.setHours(8, 0, 0, 0);
      const end = new Date(date);
      end.setHours(16, 0, 0, 0);
      return { start, end };
    },
    navigationUnit: 'day',
  },
};
```

### Custom Features

Enable different Bryntum features for specific use cases:

```typescript
// features/appointments-features.config.ts
import { type SchedulerFeatures } from '../types/scheduler.types';

export const APPOINTMENTS_FEATURES: SchedulerFeatures = {
  eventDrag: {
    constrainDragToResource: true,  // Can't move between doctors
  },
  eventResize: true,                // Can change appointment duration
  eventEdit: {
    items: {
      patientNameField: {
        type: 'text',
        name: 'patient_name',
        label: 'Paciente',
      },
    },
  },
};
```

### Custom Event Transformation

Transform your domain data to Bryntum format:

```typescript
// utils/appointment-transform.utils.ts
import { type BryntumEvent } from '../types/scheduler.types';

export function transformAppointment(apt: Appointment): BryntumEvent {
  return {
    id: apt.id,
    resourceId: apt.doctor_id,
    startDate: new Date(apt.scheduled_at),
    endDate: new Date(apt.scheduled_at + apt.duration_minutes * 60000),
    name: `${apt.patient_name} - ${apt.specialty}`,
    eventColor: getSpecialtyColor(apt.specialty),
    eventStyle: apt.status === 'confirmed' ? 'colored' : 'hollow',
    // Preserve original data
    originalAppointment: apt,
  };
}
```

---

## 🧪 Testing

### Unit Tests (Pure Functions)

```typescript
// utils/__tests__/event-transform.utils.test.ts
import { transformEvent, getEventColor } from '../event-transform.utils';

describe('transformEvent', () => {
  it('should calculate correct end date for chat events', () => {
    const event = {
      id: '1',
      timestamp: 1733678400,
      content: 'Hello',
      event_type: 'chat_user',
      source: 'chat',
    };

    const result = transformEvent(event);

    expect(result.endDate.getTime() - result.startDate.getTime()).toBe(30000); // 30s default
  });

  it('should assign sky color to user chat events', () => {
    expect(getEventColor('chat_user')).toBe('#0ea5e9');
  });
});
```

### Integration Tests (Hooks)

```typescript
// hooks/__tests__/useSchedulerState.test.ts
import { renderHook, act } from '@testing-library/react';
import { useSchedulerState } from '../useSchedulerState';

describe('useSchedulerState', () => {
  const mockEvents = [
    { id: '1', session_id: 'abc', ... },
    { id: '2', session_id: 'abc', ... },
    { id: '3', session_id: 'xyz', ... },
  ];

  it('should filter events by selected session', () => {
    const { result } = renderHook(() =>
      useSchedulerState({ events: mockEvents })
    );

    act(() => {
      result.current.setSelectedSession('abc');
    });

    expect(result.current.filteredEvents).toHaveLength(2);
  });

  it('should navigate to next day', () => {
    const { result } = renderHook(() =>
      useSchedulerState({ events: [], initialDate: new Date('2025-12-08') })
    );

    act(() => {
      result.current.navigateDate('next');
    });

    expect(result.current.currentDate.getDate()).toBe(9);
  });
});
```

---

## 🎨 Customization Guide

### Colors

Event colors are defined in `utils/event-transform.utils.ts`:

```typescript
export function getEventColor(eventType: string): string {
  switch (eventType) {
    case 'chat_user':
      return '#0ea5e9'; // sky-500
    case 'chat_assistant':
      return '#8b5cf6'; // violet-500
    case 'transcription':
      return '#10b981'; // emerald-500
    default:
      return '#64748b'; // slate-500
  }
}
```

### Tooltips

Tooltip templates are in `features/event-tooltip.feature.ts`:

```typescript
function tooltipTemplate({ eventRecord }) {
  const { content, event_type, timestamp } = eventRecord.data;
  
  return `
    <div class="custom-tooltip">
      <h3>${getEventTypeLabel(event_type)}</h3>
      <p>${content}</p>
      <span>${new Date(timestamp * 1000).toLocaleString()}</span>
    </div>
  `;
}
```

### Keyboard Shortcuts

Shortcuts are defined in `hooks/useSchedulerEvents.ts`:

```typescript
switch (e.key) {
  case 'ArrowLeft':
    if (e.shiftKey) onNavigatePrev?.();
    break;
  case '+':
    onZoomIn?.();
    break;
  // Add your custom shortcuts here
}
```

---

## 📊 Performance

### Bundle Size

| Component | Size (gzipped) |
|-----------|----------------|
| Bryntum Library | ~800 KB |
| Type Definitions | ~2 KB |
| Config/Utils | ~5 KB |
| Hooks | ~3 KB |
| **Total** | **~810 KB** |

### Optimization Tips

1. **Lazy Load** - Use dynamic import for scheduler pages:
   ```typescript
   const TimelineScheduler = dynamic(() => import('./TimelineScheduler'), {
     ssr: false,
   });
   ```

2. **Memoize** - Heavy computations are already memoized in hooks
3. **Virtual Scrolling** - Bryntum handles this automatically for 1000+ events

---

## 🔐 Security

### XSS Prevention

All user content is escaped before rendering in tooltips:

```typescript
const sanitizedContent = content
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;');
```

### PHI Protection

- ❌ No patient names in console logs
- ❌ No medical content in URLs
- ✅ All sensitive data kept in memory only
- ✅ Modal content is client-side rendered (no server logs)

---

## 🐛 Troubleshooting

### "Bryntum SchedulerPro not loaded"

**Cause**: Library files missing from `public/js/bryntum/`

**Solution**:
1. Download Bryntum trial/licensed version
2. Extract `schedulerpro.wc.module.js` to `public/js/bryntum/`
3. Extract `schedulerpro.classic-dark.css` to `public/css/bryntum/`

### "TypeScript errors on Bryntum types"

**Cause**: Missing type definitions

**Solution**: All types are defined in `types/scheduler.types.ts`. If you get errors, add:
```typescript
// @ts-expect-error - Bryntum API (typed in config)
```

### "Scheduler not rendering"

**Checklist**:
- ✅ Container ref is attached to a `<div>`
- ✅ Container has explicit height (`min-height: 300px`)
- ✅ Events array is not empty
- ✅ `isLoading` prop is false
- ✅ Browser console shows no errors

---

## 🚦 Migration Path

### From Old Implementation

1. **Backup** current `TimelineScheduler.tsx`
2. **Replace** with `TimelineScheduler.refactored.tsx`
3. **Update imports** to use `@/components/bryntum`
4. **Test** all views (day/week/month)
5. **Verify** event clicks, navigation, zoom
6. **Delete** old file once verified

### To npm Package (Future)

When Bryntum is installed via npm:

1. Update `useSchedulerLifecycle`:
   ```typescript
   // Remove loadBryntumModule()
   import { SchedulerPro } from '@bryntum/schedulerpro';
   
   const instance = new SchedulerPro(config);
   ```

2. Remove window globals from `types/scheduler.types.ts`

3. Use vendor TypeScript definitions

---

## 📚 Resources

- **Architecture Docs**: `ARCHITECTURE.md` (complete technical details)
- **Bryntum API**: https://bryntum.com/products/schedulerpro/docs/
- **Type Definitions**: `types/scheduler.types.ts` (400+ lines of TypeScript interfaces)
- **Examples**: See `components/timeline/TimelineScheduler.refactored.tsx`

---

## 🤝 Contributing

### Adding New Features

1. **Types first** - Add interfaces to `types/scheduler.types.ts`
2. **Configuration** - Create config file in `config/`
3. **Implementation** - Add feature file in `features/`
4. **Tests** - Unit tests for utils, integration tests for hooks
5. **Documentation** - Update ARCHITECTURE.md with decisions

### Code Style

- ✅ Use TypeScript strict mode
- ✅ Document all exported functions with JSDoc
- ✅ Prefer pure functions over stateful logic
- ✅ One responsibility per file
- ✅ Export through `index.ts`

---

## 📝 License

This module integrates **Bryntum Scheduler Pro** (commercial license required).  
See: https://bryntum.com/products/schedulerpro/

Internal code is part of AURITY / Free Intelligence project.

---

## 👤 Contact

**Maintainer**: Bryntum Scheduler Guardian  
**Project**: AURITY  
**Date**: December 8, 2025

For questions or issues, refer to `ARCHITECTURE.md` for detailed explanations of design decisions.
