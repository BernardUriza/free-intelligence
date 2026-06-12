const API_BASE =
  process.env.NEXT_PUBLIC_ACTIVIST_API_URL ?? 'http://localhost:8000';

export interface HealthFull {
  status: string;
  ts: string;
  active_runs: number;
  transport: string;
}

export async function getHealthFull(): Promise<HealthFull> {
  const res = await fetch(`${API_BASE}/health/full`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`/health/full returned ${res.status}`);
  return res.json();
}

export async function startWorkflow(concern: string): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ concern }),
  });
  if (!res.ok) throw new Error(`/workflow/start returned ${res.status}`);
  return res.json();
}

export async function getHistory(runId: string): Promise<unknown> {
  const res = await fetch(`${API_BASE}/workflow/${runId}/history`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`/history returned ${res.status}`);
  return res.json();
}
