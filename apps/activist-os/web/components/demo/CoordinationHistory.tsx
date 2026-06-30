import type { Handoff } from '@/lib/activist-api';

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function stepClass(h: Handoff): string {
  if (h.type === 'safety_veto') return 'hist-step hist-step--veto';
  if (h.type === 'safety_approved') return 'hist-step hist-step--approved';
  if (h.virtual) return 'hist-step hist-step--virtual';
  return 'hist-step';
}

function stepLabel(h: Handoff): string {
  if (h.type === 'safety_veto') return 'Safety VETO';
  if (h.type === 'safety_approved') return 'Safety APPROVED';
  if (h.index === 3) return 'Campaign revision';
  return cap(h.from_agent) + (h.virtual ? ' (virtual)' : '');
}

export function CoordinationHistory({ handoffs }: { handoffs: Handoff[] }) {
  return (
    <section className="fi-glass-panel fi-glass-panel--primary p-4 space-y-2">
      <p className="panel-title mb-2">Coordination History</p>
      <div className="space-y-1.5">
        {handoffs.map(h => (
          <div key={h.index} className={stepClass(h)}>
            <span className="dot" />
            <div>
              <p className="font-semibold">{stepLabel(h)}</p>
              <p className="fi-mono text-[0.65rem]" style={{ color: 'var(--fi-faint)' }}>
                {h.from_agent} → {h.to_agent}
              </p>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs pt-2" style={{ color: 'var(--fi-faint)' }}>
        Rendered from <code className="fi-mono">Transport.get_handoffs()</code> — not narrated.
      </p>
    </section>
  );
}
