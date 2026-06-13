export default function ChecklistPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="fi-glass-panel p-8 w-full max-w-2xl text-center space-y-3">
        <p className="fi-eyebrow">Pre-kickoff checklist</p>
        <h1 className="text-2xl font-bold">Checklist</h1>
        <p className="text-sm" style={{ color: 'var(--fi-muted)' }}>
          Full checklist available at the static shell while the React port is in progress.
        </p>
      </div>
    </main>
  );
}
