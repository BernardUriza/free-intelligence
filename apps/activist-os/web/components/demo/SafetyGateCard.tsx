import type { SafetyReview } from '@/lib/activist-api';

export function SafetyGateCard({ safety }: { safety: SafetyReview }) {
  return (
    <div className="fi-glass-panel p-4 space-y-3">
      <p className="panel-title">Safety Gate</p>
      {safety.veto_observed && (
        <div className="msg msg--veto space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="fi-badge fi-badge--vetoed">VETO</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--fi-muted)' }}>Campaign draft:</p>
          <p className="text-sm italic">{safety.draft_text ? `"${safety.draft_text}"` : ''}</p>
          <p className="text-sm" style={{ color: 'var(--fi-veto)' }}>{safety.veto_reason}</p>
        </div>
      )}
      {safety.approved && (
        <div className="msg msg--approved space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="fi-badge fi-badge--approved">APPROVED</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--fi-muted)' }}>Rewritten:</p>
          <p className="text-sm italic">
            {safety.rewritten_text ? `"${safety.rewritten_text}"` : ''}
          </p>
        </div>
      )}
    </div>
  );
}
