// @ts-nocheck - MSW handler types are development-only
import { HttpResponse } from 'msw';

interface SseEvent {
  event?: string;
  data: unknown;
  retry?: number;
}

/** Build a text/event-stream response from a list of events. */
export function sse(events: SseEvent[]): HttpResponse {
  const payload = events
    .map((evt) => {
      const lines: string[] = [];

      if (evt.event) {
        lines.push(`event: ${evt.event}`);
      }

      const data = typeof evt.data === 'string' ? evt.data : JSON.stringify(evt.data);
      lines.push(`data: ${data}`);

      if (typeof evt.retry === 'number') {
        lines.push(`retry: ${evt.retry}`);
      }

      lines.push('');
      return lines.join('\n');
    })
    .join('\n');

  return new HttpResponse(payload, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      Connection: 'keep-alive',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  });
}
