# EventTimeline - Componente Reutilizable

## 📋 Resumen

`EventTimeline` es un componente genérico para mostrar eventos cronológicos con configuración flexible mediante archivos de config.

**Casos de uso:**
- ✅ Timeline de transcripción (app/timeline/page.tsx)
- ✅ DialogFlow de diarización (components/medical/DialogueFlow.tsx)
- ✅ Cualquier flujo de eventos cronológicos

## 🎯 Arquitectura

```
EventTimeline (componente genérico)
    ├─ timeline-config.tsx (configuración para Timeline)
    ├─ dialogflow-config.tsx (configuración para DialogFlow)
    └─ Nuevos configs según sea necesario
```

## 📦 Archivos Creados

1. **`components/EventTimeline.tsx`** - Componente base genérico (400+ líneas)
2. **`lib/timeline-config.tsx`** - Config para eventos de transcripción
3. **`lib/dialogflow-config.tsx`** - Config para segmentos de diarización

---

## 🔧 Uso: Timeline de Transcripción

### En `app/timeline/page.tsx`

```typescript
import { EventTimeline, TimelineEvent } from '@/components/EventTimeline';
import { timelineEventConfig } from '@/lib/timeline-config';
import { getSessionDetail } from '@/lib/api/timeline';

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSession = async () => {
      setIsLoading(true);
      try {
        // Fetch from API
        const detail = await getSessionDetail(sessionId);

        // Transform API response to TimelineEvent format
        const transformedEvents: TimelineEvent[] = detail.events.map((event, idx) => ({
          id: event.event_id || `event-${idx}`,
          timestamp: event.timestamp,
          type: event.event_type,
          content: event.summary || event.what,
          metadata: {
            event_number: idx + 1,
            who: event.who,
            tags: event.tags,
            confidence: event.confidence_score,
          },
        }));

        setEvents(transformedEvents);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadSession();
  }, [sessionId]);

  return (
    <EventTimeline
      events={events}
      config={timelineEventConfig}
      isLoading={isLoading}
      error={error}
      onRefresh={() => loadSession()}
    />
  );
}
```

**Resultado visual:**
```
Session Events                             TRANSCRIPTION (4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#1  [transcription]  🕐 8:41:36 PM
    doctor lo que pasa es que me siento como un...
    ─────────────────────────────────────────────
    by system  transcription  chunk_0

#2  [transcription]  🕐 8:41:44 PM
    mi nombre es el doctor miguel lo siento...
    ─────────────────────────────────────────────
    by system  transcription  chunk_1
```

---

## 🔧 Uso: DialogFlow de Diarización

### En `components/medical/DialogueFlow.tsx` (simplificado)

```typescript
import { EventTimeline, TimelineEvent } from '@/components/EventTimeline';
import { dialogFlowConfig } from '@/lib/dialogflow-config';
import { medicalWorkflowApi, type DiarizationSegment } from '@/lib/api/medical-workflow';

export function DialogueFlow({ sessionId, audioUrl }: DialogueFlowProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSegments = async () => {
      setIsLoading(true);
      try {
        const response = await medicalWorkflowApi.getDiarizationSegments(sessionId);

        // Transform diarization segments to TimelineEvent format
        const transformedEvents: TimelineEvent[] = response.segments.map((seg, idx) => ({
          id: `seg-${idx}`,
          timestamp: seg.start_time,
          type: seg.speaker,
          content: seg.text,
          metadata: {
            speaker: seg.speaker,
            start_time: seg.start_time,
            end_time: seg.end_time,
            confidence: seg.confidence,
            improved_text: seg.improved_text,
          },
        }));

        setEvents(transformedEvents);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadSegments();
  }, [sessionId]);

  // Configure audio playback action
  const configWithAudio = {
    ...dialogFlowConfig,
    actions: {
      onPlay: (event: TimelineEvent) => {
        if (audioRef.current) {
          audioRef.current.currentTime = event.metadata.start_time;
          audioRef.current.play();
        }
      },
      onEdit: (event: TimelineEvent) => {
        setEditingId(event.id);
        setEditText(event.content);
      },
    },
  };

  return (
    <div>
      {/* Audio Player */}
      {audioUrl && (
        <audio ref={audioRef} controls src={audioUrl} />
      )}

      {/* Timeline */}
      <EventTimeline
        events={events}
        config={configWithAudio}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}
```

**Resultado visual:**
```
Revisión del Diálogo                     MÉDICO (4)  PACIENTE (3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● MÉDICO   🕐 00:12 → 00:18  (6.2s)  ⚡ 99%  ✏️
    💜 Texto mejorado (GPT-4)
    Buenos días, ¿cómo se encuentra hoy?
    ─────────────────────────────────────────────
    [Original: "buenos días como se encuentra hoy"]

● PACIENTE   🕐 00:19 → 00:25  (5.8s)  ⚡ 97%  ✏️
    Me siento muy mal, doctor...
```

---

## 🎨 Customización del Config

### Crear nuevo config personalizado

```typescript
// lib/custom-timeline-config.tsx
import type { TimelineConfig } from '@/components/EventTimeline';

export const customConfig: TimelineConfig = {
  title: 'My Custom Timeline',
  emptyMessage: 'No events yet',
  showSearch: true,
  showExport: false,
  maxHeight: 'max-h-[800px]',

  // Custom timestamp format
  formatTimestamp: (timestamp) => {
    return new Date(timestamp).toLocaleString('en-US');
  },

  // Custom colors
  getColors: (event) => {
    if (event.type === 'important') {
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'text-red-400',
        badge: 'bg-red-500',
      };
    }
    return { /* default */ };
  },

  // Custom header
  renderHeader: (event) => (
    <div>
      <h3>{event.type}</h3>
      <span>{event.timestamp}</span>
    </div>
  ),

  // Custom content
  renderContent: (event, isExpanded) => (
    <p className="text-white">{event.content}</p>
  ),

  // Custom footer
  renderFooter: (event) => (
    <div className="text-xs text-slate-500">
      ID: {event.id}
    </div>
  ),

  // Custom export
  formatExport: (events) => {
    return events.map(e => `${e.type}: ${e.content}`).join('\n');
  },

  // Custom search
  searchFilter: (event, query) => {
    return event.content.includes(query);
  },

  // Custom actions
  actions: {
    onEdit: (event) => console.log('Edit:', event.id),
    onDelete: (event) => console.log('Delete:', event.id),
  },
};
```

---

## 📊 Beneficios

### Antes (DialogueFlow de 793 líneas)
```typescript
// ❌ Componente monolítico difícil de reutilizar
export function DialogueFlow() {
  // 793 líneas de código específico para diarización
  // Imposible de usar para otros flujos
}
```

### Después (EventTimeline genérico)
```typescript
// ✅ Componente genérico + configs modulares
<EventTimeline events={data} config={timelineEventConfig} />
<EventTimeline events={data} config={dialogFlowConfig} />
<EventTimeline events={data} config={customConfig} />
```

### Métricas
- **Reutilización:** 2+ casos de uso con mismo componente base
- **Líneas de código:** DialogueFlow 793 → EventTimeline 400 + configs 200 cada uno
- **Mantenibilidad:** Config files fáciles de modificar sin tocar lógica del componente
- **Consistencia:** Mismo patrón de UI en toda la app

---

## 🚀 Próximos Pasos

1. **Migrar timeline page** a usar `EventTimeline` + `timelineEventConfig`
2. **Refactorizar DialogueFlow** a usar `EventTimeline` + `dialogFlowConfig`
3. **Eliminar código duplicado** en ambos componentes
4. **Crear tests** para EventTimeline y configs

---

## 📝 API Reference

### `TimelineEvent` Interface
```typescript
interface TimelineEvent {
  id: string;                          // Unique identifier
  timestamp: string | number;          // ISO string or seconds
  type: string;                        // Event type (transcription, diarization, etc.)
  content: string;                     // Main text content
  metadata?: Record<string, any>;      // Additional data (speaker, confidence, tags, etc.)
}
```

### `TimelineConfig` Interface
```typescript
interface TimelineConfig {
  // Header
  renderHeader?: (event: TimelineEvent) => React.ReactNode;
  renderBadge?: (event: TimelineEvent) => React.ReactNode;

  // Content
  renderContent?: (event: TimelineEvent, isExpanded: boolean) => React.ReactNode;
  renderFooter?: (event: TimelineEvent) => React.ReactNode;

  // Formatting
  formatTimestamp?: (timestamp: string | number) => string;
  getColors?: (event: TimelineEvent) => ColorScheme;

  // Features
  formatExport?: (events: TimelineEvent[]) => string;
  searchFilter?: (event: TimelineEvent, query: string) => boolean;

  // Actions
  actions?: {
    onEdit?: (event: TimelineEvent) => void;
    onPlay?: (event: TimelineEvent) => void;
    onDelete?: (event: TimelineEvent) => void;
  };

  // UI
  title?: string;
  emptyMessage?: string;
  showSearch?: boolean;
  showExport?: boolean;
  maxHeight?: string;
}
```

---

**Author:** Bernard Uriza Orozco
**Created:** 2025-11-18
**Version:** 1.0.0
