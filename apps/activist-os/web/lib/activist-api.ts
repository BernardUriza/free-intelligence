// Centralized API client for the Activist OS FastAPI backend.
// All fetches to the API go through here — components never call fetch() directly.

export const API_BASE =
  process.env.NEXT_PUBLIC_ACTIVIST_API_URL ?? 'http://localhost:8000';

export interface HealthFull {
  status: string;
  ts: string;
  active_runs: number;
  transport: string;
}

export interface Handoff {
  index: number;
  from_agent: string;
  to_agent: string;
  type: string;
  summary?: string;
  virtual: boolean;
  band_room_id: string | null;
  band_message_id: string | null;
  timestamp?: string;
}

export interface EvidenceBrief {
  title: string;
  summary: string;
  claims_count: number;
  sources_count: number;
}

export interface SafetyReview {
  draft_text: string;
  veto_reason: string;
  rewritten_text: string;
  approved: boolean;
  veto_observed: boolean;
}

export interface CampaignPacket {
  title: string;
  summary: string;
  outreach_assets_count: number;
  volunteer_tasks_count: number;
  provenance_items_count: number;
  reporter_virtual: boolean;
}

export interface Artifacts {
  evidence_brief: EvidenceBrief;
  safety_review: SafetyReview;
  campaign_packet: CampaignPacket;
}

export interface WorkflowHistory {
  run_id: string;
  status: string;
  transport: 'local' | 'band';
  veto_loop: {
    observed: boolean;
    veto_index: number | null;
    approved_index: number | null;
  };
  artifacts: Artifacts;
  handoffs: Handoff[];
}

export async function getHealthFull(base: string = API_BASE): Promise<HealthFull> {
  const res = await fetch(`${base}/health/full`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`/health/full returned ${res.status}`);
  return res.json();
}

export async function startWorkflow(
  concern: string,
  base: string = API_BASE,
): Promise<{ run_id: string }> {
  const res = await fetch(`${base}/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ concern }),
  });
  if (!res.ok) throw new Error(`/workflow/start returned ${res.status}`);
  return res.json();
}

export async function getWorkflowHistory(
  runId: string,
  base: string = API_BASE,
): Promise<WorkflowHistory> {
  const res = await fetch(`${base}/workflow/${runId}/history`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`/history returned ${res.status}`);
  return res.json();
}
