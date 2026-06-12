import type { WorkflowStreamEvent } from '@/lib/activist-api';

export function LiveEventLog({ events }: { events: WorkflowStreamEvent[] }) {
  return (
    <section className="fi-glass-panel p-4 space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <p className="panel-title">Live Event Stream</p>
        <span className="fi-mono text-[0.65rem] ml-auto" style={{ color: 'var(--fi-accent)' }}>
          Receiving workflow events…
        </span>
      </div>
      <div className="space-y-1.5">
        {events.map((e, i) => (
          <div key={i} className="hist-step">
            <span className="dot" />
            <div>
              <p className="fi-mono text-[0.65rem] uppercase" style={{ color: 'var(--fi-faint)' }}>
                {e.event_type ?? 'event'}{e.agent ? ` · ${e.agent}` : ''}
              </p>
              <p className="text-sm" style={{ color: 'var(--fi-muted)' }}>{e.summary ?? ''}</p>
            </div>
          </div>
        ))}
        {events.length === 0 && (
          <p className="text-xs" style={{ color: 'var(--fi-faint)' }}>Waiting for first event…</p>
        )}
      </div>
    </section>
  );
}
