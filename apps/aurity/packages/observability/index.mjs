export function sanitizeMessagePreview(input, max = 60) {
  const s = input ?? '';
  return s.length <= max ? s : s.slice(0, max);
}

export function hash8(input) {
  let h = 0;
  for (let i = 0; i < input.length; i++) {
    h = (h * 31 + input.charCodeAt(i)) >>> 0;
  }
  return (h >>> 0).toString(16).slice(0, 8);
}

export function createTelemetryContext(ids) {
  const context = {};
  if (ids.request_id) context.request_id = ids.request_id;
  if (ids.workflow_id) context.workflow_id = ids.workflow_id;
  if (ids.session_id) context.session_id = ids.session_id;
  if (ids.idempotency_key) context.idempotency_key = ids.idempotency_key;
  return context;
}

export async function measureAsync(label, fn) {
  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;
  return { result, duration };
}

export function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
