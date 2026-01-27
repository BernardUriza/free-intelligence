/**
 * Timeline Event Renderer
 *
 * Renders timeline events (chat messages, transcriptions) in Bryntum scheduler.
 * Shows the message content, event type icon, and timestamp.
 *
 * Card: FI-BRYNTUM-UNIFY-001
 * Created: 2026-01-14
 */

type TimelineEventRecord = {
  name?: string;        // Truncated content (50 chars)
  content?: string;     // Full content
  event_type?: string;  // 'chat_user' | 'chat_assistant' | 'transcription'
  source?: string;      // 'chat' | 'audio'
  startDate?: Date | string;
  endDate?: Date | string;
};

/**
 * Get icon for event type
 */
const typeToIcon = (eventType?: string, source?: string) => {
  const type = (eventType || '').toLowerCase();

  if (type.includes('user')) return 'U';
  if (type.includes('assistant')) return 'A';
  if (type.includes('transcription') || source === 'audio') return 'M';
  if (type.includes('soap') || type.includes('diagnosis')) return '+';
  if (type.includes('critical')) return '!';

  return 'S'; // System/default
};

/**
 * Get background color based on event type
 */
const typeToColor = (eventType?: string, source?: string) => {
  const type = (eventType || '').toLowerCase();

  if (type.includes('user')) return 'bg-sky-600/80';
  if (type.includes('assistant')) return 'bg-violet-600/80';
  if (type.includes('transcription') || source === 'audio') return 'bg-emerald-600/80';
  if (type.includes('soap') || type.includes('diagnosis')) return 'bg-cyan-600/80';
  if (type.includes('critical')) return 'bg-red-600/80';

  return 'bg-slate-600/80'; // System/default
};

/**
 * Get type label in Spanish
 */
const typeToLabel = (eventType?: string, source?: string) => {
  const type = (eventType || '').toLowerCase();

  if (type.includes('user')) return 'Usuario';
  if (type.includes('assistant')) return 'Asistente';
  if (type.includes('transcription') || source === 'audio') return 'Audio';
  if (type.includes('soap')) return 'SOAP';
  if (type.includes('diagnosis')) return 'Diagnóstico';
  if (type.includes('critical')) return 'Crítico';

  return 'Sistema';
};

/**
 * Format time
 */
const formatTime = (d?: Date | string) => {
  if (!d) return '';
  const date = typeof d === 'string' ? new Date(d) : d;
  try {
    return date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
};

/**
 * Timeline Event Renderer
 *
 * Returns DomConfig for Bryntum WebComponent bundle compatibility.
 */
export function timelineEventRenderer({ eventRecord }: { eventRecord: TimelineEventRecord }) {
  const content = eventRecord.content || eventRecord.name || 'Sin contenido';
  const eventType = eventRecord.event_type;
  const source = eventRecord.source;
  const icon = typeToIcon(eventType, source);
  const bgColor = typeToColor(eventType, source);
  const label = typeToLabel(eventType, source);
  const time = formatTime(eventRecord.startDate);

  // DomConfig for Bryntum - framework-agnostic
  return {
    className: `fi-timeline-event flex items-start gap-2 rounded-md shadow-sm ${bgColor} text-white text-[11px] leading-tight h-full overflow-hidden p-2`,
    children: [
      // Icon
      {
        tag: 'div',
        className: 'flex-shrink-0 text-sm',
        html: icon,
      },
      // Content area
      {
        tag: 'div',
        className: 'flex-1 min-w-0 overflow-hidden',
        children: [
          // Header: Type label + Time
          {
            tag: 'div',
            className: 'flex items-center justify-between gap-2 mb-0.5',
            children: [
              {
                tag: 'span',
                className: 'font-semibold text-[10px] uppercase tracking-wide opacity-90',
                html: label,
              },
              {
                tag: 'span',
                className: 'text-[9px] opacity-75 whitespace-nowrap',
                html: time,
              },
            ],
          },
          // Message content
          {
            tag: 'div',
            className: 'text-[11px] line-clamp-2 opacity-95',
            html: content,
          },
        ],
      },
    ],
  };
}

export default timelineEventRenderer;
