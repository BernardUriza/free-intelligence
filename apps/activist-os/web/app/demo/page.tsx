export default function DemoPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div
        className="rounded-2xl p-8 w-full max-w-2xl text-center"
        style={{ background: 'var(--fi-surface)', border: '1px solid var(--fi-border)' }}
      >
        <p className="font-mono text-xs tracking-widest uppercase mb-3" style={{ color: 'var(--fi-faint)' }}>
          Coming next
        </p>
        <h1 className="text-2xl font-bold mb-2">Coordination Demo</h1>
        <p style={{ color: 'var(--fi-muted)' }} className="text-sm">
          This route will port <code className="font-mono">demo.html</code> into React —
          consuming <code className="font-mono">/workflow/&#123;id&#125;/history</code> and
          the live SSE stream.
        </p>
      </div>
    </main>
  );
}
