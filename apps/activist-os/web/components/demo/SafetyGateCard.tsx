import type { SafetyReview } from '@/lib/activist-api';

export function SafetyGateCard({ safety }: { safety: SafetyReview }) {
  return (
    <div className="fi-glass-panel fi-glass-panel--critical p-5 space-y-3">
      <p className="panel-title">Safety Gate</p>
      {safety.veto_observed && (
        <div className="msg msg--veto veto-stage space-y-2">
          <div className="flex items-center gap-2">
            <span className="fi-badge fi-badge--vetoed">VETO</span>
          </div>
          <p className="stage-key">Campaign draft</p>
          <p className="stage-text italic">{safety.draft_text ? `"${safety.draft_text}"` : ''}</p>
          <p className="stage-key" style={{ color: 'color-mix(in srgb, var(--fi-veto), transparent 30%)' }}>Blocked reason</p>
          <p className="stage-text" style={{ color: 'var(--fi-veto)' }}>{safety.veto_reason}</p>
        </div>
      )}
      {safety.veto_observed && safety.approved && (
        <div className="veto-loop-connector" aria-hidden="true">
          <span>campaign revision → re-review</span>
        </div>
      )}
      {safety.approved && (
        <div className="msg msg--approved veto-stage space-y-2">
          <div className="flex items-center gap-2">
            <span className="fi-badge fi-badge--approved">APPROVED</span>
          </div>
          <p className="stage-key">Approved rewrite</p>
          <p className="stage-text italic">
            {safety.rewritten_text ? `"${safety.rewritten_text}"` : ''}
          </p>
        </div>
      )}
    </div>
  );
}
