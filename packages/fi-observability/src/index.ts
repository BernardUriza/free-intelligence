export interface TelemetryIds {
  request_id?: string;
  workflow_id?: string;
  session_id?: string;
  idempotency_key?: string;
}

export function sanitizeMessagePreview(input: string, max = 60): string {
  const s = input ?? '';
  return s.length <= max ? s : s.slice(0, max);
}

export function hash8(input: string): string {
  let h = 0;
  for (let i = 0; i < input.length; i++) h = (h * 31 + input.charCodeAt(i)) >>> 0;
  return (h >>> 0).toString(16).slice(0, 8);
}
