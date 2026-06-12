export default function ChecklistPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div
        className="rounded-2xl p-8 w-full max-w-2xl text-center"
        style={{ background: 'var(--fi-surface)', border: '1px solid var(--fi-border)' }}
      >
        <p className="font-mono text-xs tracking-widest uppercase mb-3" style={{ color: 'var(--fi-faint)' }}>
          Coming next
        </p>
        <h1 className="text-2xl font-bold mb-2">Pre-Kickoff Checklist</h1>
        <p style={{ color: 'var(--fi-muted)' }} className="text-sm">
          This route will replace <code className="font-mono">checklist.html</code>.
        </p>
      </div>
    </main>
  );
}
