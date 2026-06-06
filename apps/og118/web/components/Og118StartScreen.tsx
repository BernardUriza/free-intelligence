'use client';

/**
 * og118 start screen — the chat-first first paint. The intellectual framing
 * (the Og tile, "what is this", the glassmorphism) lives HERE, integrated into
 * the app's empty state, not on a separate landing page. In step 3 this is fed
 * to fi-glass's ChatStartScreen / the ChatHook `customEmptyState` slot; for now
 * it stands alone so we can verify the scaffold + theme render.
 */
export function Og118StartScreen() {
  return (
    <main
      style={{
        minHeight: '100dvh',
        display: 'grid',
        placeItems: 'center',
        padding: '2rem',
      }}
    >
      <section
        className="glass"
        style={{
          maxWidth: 560,
          width: '100%',
          textAlign: 'center',
          padding: '2.5rem 2rem',
          borderRadius: 20,
          background: 'rgba(15, 23, 42, 0.55)',
          backdropFilter: 'blur(var(--glass-blur, 12px)) saturate(var(--glass-saturation, 180%))',
          border: '1px solid var(--glass-border, rgba(255,255,255,0.18))',
          boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/og-tile.png"
          alt="Oganesson — element 118"
          width={220}
          style={{ maxWidth: '70%', height: 'auto', filter: 'drop-shadow(0 8px 24px rgba(52,211,153,0.15))' }}
        />

        <h1 style={{ margin: '1.5rem 0 0.25rem', fontSize: '2rem', letterSpacing: '-0.02em' }}>
          og118<span style={{ color: 'var(--og-accent, #34d399)' }}>.ai</span>
        </h1>

        <p style={{ margin: '0 0 1rem', color: '#94a3b8', fontSize: '0.95rem' }}>
          Og · 118 · Oganesson — synthetic, the heaviest known, the end of the table.
        </p>

        <p style={{ margin: 0, color: '#cbd5e1', lineHeight: 1.6 }}>
          A personal thinking companion on the Free Intelligence substrate.
          Glass-box by design — you see the reasoning, not just the answer.
        </p>

        <p style={{ marginTop: '1.75rem', color: '#475569', fontSize: '0.8rem' }}>
          soon. something radioactive here.
        </p>
      </section>
    </main>
  );
}
