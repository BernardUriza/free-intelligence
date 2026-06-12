'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  API_BASE,
  getWorkflowHistory,
  startWorkflow,
  type Handoff,
  type WorkflowHistory,
} from '@/lib/activist-api';
import { SourceBadge, TransportBadge, type SourceState } from '@/components/demo/StatusBadge';
import { CoordinationHistory } from '@/components/demo/CoordinationHistory';
import { SafetyGateCard } from '@/components/demo/SafetyGateCard';
import { CampaignPacketCard } from '@/components/demo/CampaignPacketCard';

// Reproducible mock — hand-written demo copy lives ONLY here, behind the
// MOCK FALLBACK badge. The live API derives artifacts from real payloads.
const MOCK_HISTORY: WorkflowHistory = {
  run_id: 'demo-mock-run',
  status: 'completed',
  transport: 'local',
  veto_loop: { observed: true, veto_index: 2, approved_index: 4 },
  handoffs: [
    { index: 0, from_agent: 'evidence', to_agent: 'campaign', type: 'evidence_complete', virtual: false, band_room_id: null, band_message_id: null },
    { index: 1, from_agent: 'campaign', to_agent: 'safety', type: 'safety_request', virtual: false, band_room_id: null, band_message_id: null },
    { index: 2, from_agent: 'safety', to_agent: 'campaign', type: 'safety_veto', virtual: false, band_room_id: null, band_message_id: null },
    { index: 3, from_agent: 'campaign', to_agent: 'safety', type: 'safety_request', virtual: false, band_room_id: null, band_message_id: null },
    { index: 4, from_agent: 'safety', to_agent: 'outreach', type: 'safety_approved', virtual: false, band_room_id: null, band_message_id: null },
    { index: 5, from_agent: 'outreach', to_agent: 'coordinator', type: 'outreach_ready', virtual: false, band_room_id: null, band_message_id: null },
    { index: 6, from_agent: 'coordinator', to_agent: 'reporter', type: 'tasks_ready', virtual: true, band_room_id: null, band_message_id: null },
    { index: 7, from_agent: 'reporter', to_agent: 'system', type: 'packet_ready', virtual: true, band_room_id: null, band_message_id: null },
  ],
  artifacts: {
    evidence_brief: {
      title: 'Restaurant X claims 100% compostable packaging, but local waste systems do not process it.',
      summary: '3 claims verified — 2 usable in campaign, 4 sources with provenance tiers attached.',
      claims_count: 3,
      sources_count: 4,
    },
    safety_review: {
      draft_text: 'Restaurant X is lying to its customers about eco-friendly packaging.',
      veto_reason: 'defamation: unsupported accusation against a named target — blocked.',
      rewritten_text: "Available evidence does not support the restaurant's 'compostable' claim under local disposal conditions.",
      approved: true,
      veto_observed: true,
    },
    campaign_packet: {
      title: 'Campaign packet — compostable packaging claim',
      summary: 'Assembled from 8 coordinated handoffs; safety audit log included (approved).',
      outreach_assets_count: 3,
      volunteer_tasks_count: 4,
      provenance_items_count: 4,
      reporter_virtual: true,
    },
  },
};

const HANDOFF_BLURBS: Record<string, string> = {
  evidence_complete: 'Evidence brief ready — claims verified with provenance tiers.',
  safety_request: 'Campaign plan submitted for the five safety checks.',
  safety_veto: 'VETO — blocked items returned to Campaign with precise reasons.',
  safety_approved: 'APPROVED — the only status that unlocks public action.',
  outreach_ready: "Outreach pack drafted in the community's language.",
  tasks_ready: 'Volunteer task board assembled.',
  packet_ready: 'Campaign packet compiled — audit log included.',
};

const DEFAULT_CONCERN =
  'Cafe Verde claims its packaging is compostable, but the local waste facility does not accept compostable packaging.';

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function msgClass(h: Handoff): string {
  return (
    'msg' +
    (h.type === 'safety_veto' ? ' msg--veto' : '') +
    (h.type === 'safety_approved' ? ' msg--approved' : '') +
    (h.virtual ? ' msg--virtual' : '')
  );
}

function ConversationSurface({ handoffs, roomId }: { handoffs: Handoff[]; roomId: string | null }) {
  return (
    <section className="fi-glass-panel p-4 space-y-2.5">
      <div className="flex items-center gap-2 mb-1">
        <p className="panel-title">Agent Conversation Surface</p>
        {roomId && (
          <span className="fi-mono text-[0.65rem] ml-auto" style={{ color: 'var(--fi-faint)' }}>
            room {roomId}
          </span>
        )}
      </div>
      <div className="space-y-2.5">
        {handoffs.map(h => (
          <div key={h.index} className={msgClass(h)}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="agent text-sm">{cap(h.from_agent)}</span>
              {h.virtual ? (
                <span className="fi-mono text-[0.65rem]" style={{ color: 'var(--fi-evidence)' }}>
                  [virtual · backend event]
                </span>
              ) : (
                <span className="mention">@{cap(h.to_agent)}</span>
              )}
              <span className="fi-mono text-[0.65rem] uppercase" style={{ color: 'var(--fi-faint)' }}>
                {h.type}
              </span>
              {h.band_message_id && (
                <span className="fi-mono text-[0.6rem]" style={{ color: 'var(--fi-faint)' }}>
                  msg {h.band_message_id}
                </span>
              )}
            </div>
            <p className="text-sm mt-1" style={{ color: 'var(--fi-muted)' }}>
              {HANDOFF_BLURBS[h.type] || h.summary || ''}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function DemoClient() {
  const searchParams = useSearchParams();
  const urlRunId = searchParams.get('run_id');
  const apiBase = searchParams.get('api') || API_BASE;

  const [source, setSource] = useState<SourceState>(urlRunId ? 'STARTING' : 'MOCK FALLBACK');
  const [history, setHistory] = useState<WorkflowHistory | null>(urlRunId ? null : MOCK_HISTORY);
  const [sourceLabel, setSourceLabel] = useState(
    urlRunId ? `loading · ${apiBase}` : 'reproducible mock (pass ?run_id=… for a live run)',
  );
  const [concern, setConcern] = useState(DEFAULT_CONCERN);
  const [startStatus, setStartStatus] = useState(
    urlRunId ? '' : 'IDLE — mock shown until a workflow runs.',
  );
  const [starting, setStarting] = useState(false);
  // Hide the start panel once a run owns the URL (deep link or just-started run).
  const [activeRunId, setActiveRunId] = useState<string | null>(urlRunId);
  const [errorDetail, setErrorDetail] = useState('');

  const showLive = useCallback((data: WorkflowHistory, base: string) => {
    setHistory(data);
    setSource('LIVE API');
    setSourceLabel(`live · ${base}`);
  }, []);

  // Deep link: fetch the run's history. A failed fetch is an ERROR state —
  // never a silent mock fallback (the run was explicitly requested).
  useEffect(() => {
    if (!urlRunId) return;
    let cancelled = false;
    getWorkflowHistory(urlRunId, apiBase)
      .then(data => { if (!cancelled) showLive(data, apiBase); })
      .catch(err => {
        if (cancelled) return;
        setSource('ERROR');
        setSourceLabel(`error · ${apiBase}`);
        setErrorDetail(`Could not fetch run ${urlRunId}: ${String(err)}`);
        setHistory(null);
      });
    return () => { cancelled = true; };
  }, [urlRunId, apiBase, showLive]);

  async function handleStart() {
    setStarting(true);
    setSource('STARTING');
    setStartStatus('Starting workflow…');
    try {
      const { run_id } = await startWorkflow(concern.trim(), apiBase);
      const url = new URL(window.location.href);
      url.searchParams.set('run_id', run_id);
      window.history.replaceState(null, '', url);
      setActiveRunId(run_id);
      // Stub agents finish in milliseconds; poll briefly until the run settles.
      let data: WorkflowHistory | null = null;
      for (let i = 0; i < 16; i++) {
        try {
          data = await getWorkflowHistory(run_id, apiBase);
          if (['completed', 'blocked', 'error'].includes(data.status)) break;
        } catch {
          // run may not be registered yet
        }
        await new Promise(r => setTimeout(r, 500));
      }
      if (!data) throw new Error('history never became available');
      showLive(data, apiBase);
      setStartStatus('');
    } catch (err) {
      console.error('workflow start failed:', err);
      setSource('ERROR');
      setErrorDetail(String(err));
      setStartStatus('Could not start live workflow. Check API URL and backend logs.');
    } finally {
      setStarting(false);
    }
  }

  const roomId = history?.handoffs.find(h => h.band_room_id)?.band_room_id ?? null;
  const hasVirtual = history?.handoffs.some(h => h.virtual) ?? false;

  return (
    <div className="min-h-screen">
      <div className="fi-shell-bg" />

      <header className="max-w-[1500px] mx-auto px-5 pt-6 pb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-bold tracking-tight flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/branding/emblem.png" alt="Activist OS" width={28} height={28} style={{ borderRadius: 6, opacity: 0.92 }} />
          Activist OS — Coordination Demo
        </h1>
        <TransportBadge transport={history?.transport ?? 'local'} />
        <SourceBadge state={source} />
        <span className="fi-badge fi-badge--provenance">PROVENANCE</span>
        {hasVirtual && <span className="fi-badge fi-badge--virtual">VIRTUAL REPORTER</span>}
        {history && (
          <span className="fi-mono text-xs" style={{ color: 'var(--fi-faint)' }}>
            run {history.run_id}
          </span>
        )}
        <span className="fi-mono text-xs ml-auto" style={{ color: 'var(--fi-faint)' }}>
          {sourceLabel}
        </span>
      </header>

      {!activeRunId && (
        <section className="max-w-[1500px] mx-auto px-5 pb-4">
          <div className="fi-glass-panel p-4 flex flex-wrap items-center gap-3">
            <label className="panel-title" htmlFor="concern-input">Describe a civic concern</label>
            <input
              id="concern-input"
              type="text"
              value={concern}
              onChange={e => setConcern(e.target.value)}
              className="flex-1 min-w-[280px] bg-transparent rounded-lg px-3 py-2 text-sm outline-none"
              style={{ border: '1px solid var(--fi-border)', color: 'var(--fi-text)' }}
            />
            <button
              onClick={handleStart}
              disabled={starting}
              className="rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide cursor-pointer disabled:opacity-50"
              style={{
                fontFamily: 'var(--fi-font-mono)',
                color: 'var(--fi-accent)',
                border: '1px solid color-mix(in srgb, var(--fi-accent), transparent 60%)',
                background: 'color-mix(in srgb, var(--fi-accent), transparent 90%)',
              }}
            >
              Run workflow
            </button>
            <span className="fi-mono text-xs" style={{ color: 'var(--fi-faint)' }}>{startStatus}</span>
          </div>
        </section>
      )}

      {source === 'ERROR' && !history && (
        <section className="max-w-[1500px] mx-auto px-5 pb-4">
          <div className="fi-glass-panel p-6 space-y-2" style={{ borderColor: 'color-mix(in srgb, var(--fi-veto), transparent 45%)' }}>
            <p className="panel-title" style={{ color: 'var(--fi-veto)' }}>Error</p>
            <p className="text-sm" style={{ color: 'var(--fi-muted)' }}>{errorDetail}</p>
            <p className="text-xs" style={{ color: 'var(--fi-faint)' }}>
              The API at {apiBase} is unreachable or the run does not exist. No mock is shown for
              an explicitly requested run.
            </p>
          </div>
        </section>
      )}

      {history && (
        <main className="max-w-[1500px] mx-auto px-5 pb-10 grid grid-cols-1 lg:grid-cols-[290px_minmax(0,1fr)_360px] gap-4 items-start">
          <CoordinationHistory handoffs={history.handoffs} />
          <ConversationSurface handoffs={history.handoffs} roomId={roomId} />
          <section className="space-y-4">
            <div className="fi-glass-panel p-4 space-y-2">
              <p className="panel-title">Evidence Brief</p>
              <p className="text-sm font-semibold">{history.artifacts.evidence_brief?.title}</p>
              <p className="text-xs" style={{ color: 'var(--fi-muted)' }}>
                {history.artifacts.evidence_brief?.summary}
              </p>
            </div>
            <SafetyGateCard safety={history.artifacts.safety_review} />
            <CampaignPacketCard
              packet={history.artifacts.campaign_packet}
              evidence={history.artifacts.evidence_brief}
            />
            {history.artifacts.campaign_packet?.reporter_virtual && (
              <div className="fi-glass-panel p-4 space-y-1">
                <p className="panel-title">Why a virtual reporter?</p>
                <p className="text-xs" style={{ color: 'var(--fi-muted)' }}>
                  Reporter is virtualized to respect Band room participant limits while preserving
                  the canonical workflow history. Its handoffs ride as Band room events, emitted by
                  the backend.
                </p>
              </div>
            )}
          </section>
        </main>
      )}

      <footer
        className="max-w-[1500px] mx-auto px-5 pb-8 pt-4 flex items-center gap-3"
        style={{ borderTop: '1px solid var(--fi-border-soft)', marginTop: '2rem' }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/branding/logo-white.png" alt="Activist OS" style={{ height: 22, width: 'auto', opacity: 0.55 }} />
        <span className="fi-mono text-xs" style={{ color: 'var(--fi-faint)' }}>
          Evidence. Coordination. Safety.
        </span>
        <a href="/" className="fi-mono text-xs ml-auto" style={{ color: 'var(--fi-faint)', textDecoration: 'none' }}>
          ← Home
        </a>
      </footer>
    </div>
  );
}
