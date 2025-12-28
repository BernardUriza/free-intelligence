/**
 * Event Tooltip Feature Configuration
 * 
 * Generates rich HTML tooltips for timeline events.
 * Shows event type, timestamp, content preview, and duration.
 */

import type { EventTooltipFeature } from '../types/scheduler.types';
import { getEventColor, getEventTypeLabel } from '../utils/event-transform.utils';

/**
 * Tooltip template generator
 * Returns HTML string for Bryntum tooltip rendering
 */
function tooltipTemplate({ eventRecord }: { eventRecord: { data: Record<string, unknown> } }): string {
  const content = (eventRecord.data.content as string) || '';
  const preview = content.length > 200 ? content.slice(0, 200) + '...' : content;
  const eventType = eventRecord.data.event_type as string;
  const timestamp = new Date((eventRecord.data.timestamp as number) * 1000);
  const duration = eventRecord.data.duration as number | undefined;
  const color = getEventColor(eventType);
  const label = getEventTypeLabel(eventType);

  return `
    <div class="p-3 max-w-sm">
      <div class="flex items-center gap-2 mb-2">
        <span 
          class="w-2 h-2 rounded-full" 
          style="background-color: ${color}"
        ></span>
        <span class="font-medium text-white text-sm">${label}</span>
      </div>
      
      <div class="text-xs text-slate-400 mb-2">
        ${timestamp.toLocaleString('es-MX')}
      </div>
      
      <div class="text-sm text-slate-300 whitespace-pre-wrap">${preview}</div>
      
      ${duration ? `<div class="text-xs text-slate-500 mt-2">Duración: ${duration.toFixed(1)}s</div>` : ''}
    </div>
  `;
}

/**
 * Event Tooltip Feature Configuration
 */
export const EVENT_TOOLTIP_CONFIG: EventTooltipFeature = {
  template: tooltipTemplate,
};
