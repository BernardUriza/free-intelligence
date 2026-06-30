import Link from 'next/link';

export const metadata = {
  title: 'Activist OS — Safe, evidence-backed civic advocacy workflows',
  description:
    'Coordinate specialized agents to turn a community concern into a verified campaign packet — with provenance, safety review, and human-action tasks before anything goes public.',
};

export default function Home() {
  return (
    <>
      {/* ── Nav ──────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-50 backdrop-blur-md"
        style={{
          background: 'color-mix(in srgb, var(--fi-bg), transparent 25%)',
          borderBottom: '1px solid var(--fi-border-soft)',
        }}
      >
        <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span
              className="grid place-items-center w-8 h-8 rounded-lg fi-mono font-bold text-sm"
              style={{
                background: 'var(--fi-surface-strong)',
                border: '1px solid var(--fi-border)',
                color: 'var(--fi-accent)',
              }}
            >
              ⬡
            </span>
            <span className="font-semibold tracking-tight">Activist OS</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted">
            <a href="#workflow" className="hover:text-white transition">Workflow</a>
            <a href="#veto" className="hover:text-white transition">Safety veto</a>
            <a href="#packet" className="hover:text-white transition">Output</a>
            <a href="#architecture" className="hover:text-white transition">Architecture</a>
          </div>
          <a
            href="#demo"
            className="fi-btn fi-btn--ghost text-sm py-2 px-4"
          >
            Launch demo
          </a>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-6">

        {/* ── 1. Hero + agent flow ──────────────────────────────── */}
        <section className="grid lg:grid-cols-2 gap-12 items-center py-20 lg:py-28">
          <div className="fi-rise">
            <p className="fi-eyebrow mb-5">Regulated &amp; High-Stakes Workflows</p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-[1.05] tracking-tight mb-6">
              Safe, evidence-backed<br />civic advocacy workflows.
            </h1>
            <p className="text-lg text-muted leading-relaxed mb-8 max-w-xl">
              Coordinate specialized agents to turn a community concern into a verified
              campaign packet — with provenance, safety review, and human-action tasks{' '}
              <span className="text-white font-medium">before anything goes public.</span>
            </p>
            <div className="flex flex-wrap gap-3 mb-10">
              <a href="#demo" className="fi-btn fi-btn--primary">Launch demo →</a>
              <a href="#workflow" className="fi-btn fi-btn--ghost">View agent flow</a>
            </div>
            <div className="fi-mono text-sm text-faint space-y-1">
              <p><span style={{ color: 'var(--fi-accent)' }}>Band</span> coordinates the agents.</p>
              <p><span style={{ color: 'var(--fi-evidence)' }}>FI</span> preserves memory and provenance.</p>
              <p><span style={{ color: 'var(--fi-safety)' }}>Safety</span> gates every public action.</p>
            </div>
          </div>

          {/* Agent flow visual */}
          <div className="fi-glass-panel p-6 lg:p-8 fi-rise" style={{ animationDelay: '.1s' }}>
            <p className="fi-eyebrow mb-5">Agent flow</p>
            <div className="space-y-3 fi-mono text-sm">
              <div className="fi-agent-node fi-evidence-b px-4 py-3 flex items-center justify-between">
                <span>Evidence</span>
                <span className="fi-badge fi-badge--verified">verified</span>
              </div>
              <div className="text-center fi-arrow">↓</div>
              <div
                className="rounded-xl p-3"
                style={{
                  border: '1px dashed color-mix(in srgb, var(--fi-safety), transparent 55%)',
                  background: 'color-mix(in srgb, var(--fi-safety), transparent 95%)',
                }}
              >
                <p className="text-[.6rem] tracking-widest uppercase text-faint mb-2 px-1">veto loop</p>
                <div className="fi-agent-node px-4 py-3 flex items-center justify-between mb-2">
                  <span>Campaign</span>
                  <span className="fi-arrow">⇄</span>
                </div>
                <div className="fi-agent-node fi-safety px-4 py-3 flex items-center justify-between">
                  <span>Safety</span>
                  <span className="fi-badge fi-badge--review">review</span>
                </div>
              </div>
              <div className="text-center fi-arrow">↓</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="fi-agent-node px-4 py-3">Outreach</div>
                <div className="fi-agent-node px-4 py-3">Coordinator</div>
              </div>
              <div className="text-center fi-arrow">↓</div>
              <div className="fi-agent-node fi-approved px-4 py-3 flex items-center justify-between">
                <span>Reporter</span>
                <span className="fi-badge fi-badge--approved">packet</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── 2. The high-stakes problem ──────────────────────── */}
        <section className="py-16 border-t" style={{ borderColor: 'var(--fi-border-soft)' }}>
          <p className="fi-eyebrow mb-3">The high-stakes problem</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3 max-w-2xl">
            Advocacy is easy to start and easy to get wrong.
          </h2>
          <p className="text-muted max-w-2xl mb-10">
            Grassroots groups carry real legal and safety exposure with no ops layer to catch it.
          </p>
          <div className="grid md:grid-cols-3 gap-5">
            <div className="fi-glass-panel p-6">
              <div className="fi-mono text-2xl mb-4" style={{ color: 'var(--fi-veto)' }}>01</div>
              <h3 className="font-semibold text-lg mb-2">Unsupported claims create legal risk.</h3>
              <p className="text-muted text-sm leading-relaxed">A defamation suit is the fastest way for a corporation to silence a local group. One overstated accusation is all it takes.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <div className="fi-mono text-2xl mb-4" style={{ color: 'var(--fi-safety)' }}>02</div>
              <h3 className="font-semibold text-lg mb-2">Public campaigns can accidentally escalate.</h3>
              <p className="text-muted text-sm leading-relaxed">Targeting a person instead of a practice, or leaking private data, turns advocacy into harassment — even when the cause is right.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <div className="fi-mono text-2xl mb-4" style={{ color: 'var(--fi-accent)' }}>03</div>
              <h3 className="font-semibold text-lg mb-2">Volunteer teams burn out on coordination.</h3>
              <p className="text-muted text-sm leading-relaxed">Groups dissolve because organizers drown in email, spreadsheets, and drafting — not because the cause died.</p>
            </div>
          </div>
        </section>

        {/* ── 3. How the workflow works ────────────────────────── */}
        <section
          id="workflow"
          className="py-16 border-t"
          style={{ borderColor: 'var(--fi-border-soft)', scrollMarginTop: '5rem' }}
        >
          <p className="fi-eyebrow mb-3">How the workflow works</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3 max-w-2xl">
            Six specialized agents, one governed handoff chain.
          </h2>
          <p className="text-muted max-w-2xl mb-10">
            Each agent owns one role and exchanges structured context through Band. The
            coordination is visible — not narrated.
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div className="fi-glass-panel p-6 fi-evidence-b">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg">Evidence</h3>
                <span className="fi-badge fi-badge--verified">verified</span>
              </div>
              <p className="text-muted text-sm leading-relaxed">Finds and verifies claims, attaching a provenance tier to every source.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-3">Campaign</h3>
              <p className="text-muted text-sm leading-relaxed">Turns verified evidence into a campaign narrative — never beyond what the evidence supports.</p>
            </div>
            <div className="fi-glass-panel p-6 fi-safety">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg">Safety</h3>
                <span className="fi-badge fi-badge--review">veto power</span>
              </div>
              <p className="text-muted text-sm leading-relaxed">Blocks doxxing, harassment, unsupported accusations, and unsafe escalation before anything ships.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-3">Outreach</h3>
              <p className="text-muted text-sm leading-relaxed">Drafts posts, emails, flyers, and public copy — in the language of the community.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-3">Coordinator</h3>
              <p className="text-muted text-sm leading-relaxed">Converts the approved strategy into a concrete volunteer task board.</p>
            </div>
            <div className="fi-glass-panel p-6 fi-approved">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg">Reporter</h3>
                <span className="fi-badge fi-badge--approved">packet</span>
              </div>
              <p className="text-muted text-sm leading-relaxed">Assembles the final provenance and audit packet, including every safety verdict.</p>
            </div>
          </div>
        </section>

        {/* ── 4. Safety veto loop ──────────────────────────────── */}
        <section
          id="veto"
          className="py-16 border-t"
          style={{ borderColor: 'var(--fi-border-soft)', scrollMarginTop: '5rem' }}
        >
          <p className="fi-eyebrow mb-3" style={{ color: 'var(--fi-safety)' }}>The safety veto loop</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3 max-w-2xl">
            Safety can veto the campaign before public release.
          </h2>
          <p className="text-muted max-w-2xl mb-10">
            This is not a prompt chain. It is a governed workflow — and the rejection is on the record.
          </p>
          <div className="fi-glass-panel p-6 lg:p-8 max-w-3xl">
            <div className="space-y-4 fi-mono text-sm">
              <div className="fi-agent-node px-5 py-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-faint text-xs tracking-widest uppercase">Campaign draft</span>
                </div>
                <p className="text-white leading-relaxed">&ldquo;Restaurant X is lying to its customers.&rdquo;</p>
              </div>
              <div className="flex items-center gap-2 pl-1 text-faint">
                <span className="fi-arrow">↓</span>
                <span className="text-xs">sent to Safety via Band</span>
              </div>
              <div className="fi-agent-node fi-veto px-5 py-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-faint text-xs tracking-widest uppercase">Safety verdict</span>
                  <span className="fi-badge fi-badge--vetoed">vetoed</span>
                </div>
                <p className="leading-relaxed" style={{ color: 'var(--fi-veto)' }}>
                  VETO — unsupported accusation. Requires stronger evidence or softer language.
                </p>
              </div>
              <div className="flex items-center gap-2 pl-1 text-faint">
                <span className="fi-arrow">↻</span>
                <span className="text-xs">returned to Campaign for revision</span>
              </div>
              <div className="fi-agent-node fi-approved px-5 py-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-faint text-xs tracking-widest uppercase">Rewritten &amp; approved</span>
                  <span className="fi-badge fi-badge--approved">approved</span>
                </div>
                <p className="text-white leading-relaxed">
                  &ldquo;Available evidence does not support the restaurant&rsquo;s &lsquo;compostable&rsquo;
                  claim in local disposal conditions.&rdquo;
                </p>
              </div>
            </div>
          </div>
          <p className="text-muted text-sm mt-6 max-w-2xl">
            The rejected revision ships <span className="text-white">inside the packet</span> —
            governance that only shows its approvals is marketing.
          </p>
        </section>

        {/* ── 5. Campaign packet ───────────────────────────────── */}
        <section
          id="packet"
          className="py-16 border-t"
          style={{ borderColor: 'var(--fi-border-soft)', scrollMarginTop: '5rem' }}
        >
          <p className="fi-eyebrow mb-3">The output</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3 max-w-2xl">
            A campaign packet, ready for humans to execute.
          </h2>
          <p className="text-muted max-w-2xl mb-10">
            Hours of specialist work, governed and auditable. The system assembles it; humans hold the send button.
          </p>
          <div className="fi-glass-panel p-6 lg:p-8 max-w-3xl">
            <ul className="grid sm:grid-cols-2 gap-x-8 gap-y-4 fi-mono text-sm">
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-evidence)' }}>▪</span> Evidence brief</li>
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-safety)' }}>▪</span> Risk-reviewed campaign message</li>
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-accent)' }}>▪</span> Outreach copy</li>
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-accent)' }}>▪</span> Volunteer task plan</li>
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-evidence)' }}>▪</span> Source / provenance report</li>
              <li className="flex items-center gap-3"><span style={{ color: 'var(--fi-approved)' }}>▪</span> Safety audit log</li>
            </ul>
          </div>
        </section>

        {/* ── 6. Architecture ─────────────────────────────────── */}
        <section
          id="architecture"
          className="py-16 border-t"
          style={{ borderColor: 'var(--fi-border-soft)', scrollMarginTop: '5rem' }}
        >
          <p className="fi-eyebrow mb-3">The architecture</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-10 max-w-2xl">
            Why Band + FI + Safety.
          </h2>
          <div className="grid md:grid-cols-3 gap-5">
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-2" style={{ color: 'var(--fi-accent)' }}>Band</h3>
              <p className="text-muted text-sm leading-relaxed">Coordinates agent handoffs, shared context, and workflow state — the visible coordination layer.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-2" style={{ color: 'var(--fi-evidence)' }}>FI</h3>
              <p className="text-muted text-sm leading-relaxed">Stores provenance, memory, evidence trails, and audit artifacts across the whole run.</p>
            </div>
            <div className="fi-glass-panel p-6">
              <h3 className="font-semibold text-lg mb-2" style={{ color: 'var(--fi-safety)' }}>Safety</h3>
              <p className="text-muted text-sm leading-relaxed">Reviews every public-facing action before release. <span className="text-white">Legal-risk-aware by design.</span></p>
            </div>
          </div>
          <p className="fi-mono text-sm text-faint mt-8">
            Insult AI cross-examined claims. <span className="text-white">Activist OS coordinates evidence-backed action.</span>
          </p>
        </section>

        {/* ── 7. Demo CTA ─────────────────────────────────────── */}
        <section
          id="demo"
          className="py-20 lg:py-28 border-t"
          style={{ borderColor: 'var(--fi-border-soft)', scrollMarginTop: '5rem' }}
        >
          <div
            className="fi-glass-panel p-10 lg:p-14 text-center"
            style={{ background: 'color-mix(in srgb, var(--fi-surface), var(--fi-accent) 4%)' }}
          >
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4 max-w-2xl mx-auto">
              Turn a community concern into safe, coordinated action.
            </h2>
            <p className="text-muted max-w-xl mx-auto mb-8">
              First use case: vegan and ecological community campaigns, including
              greenwashing detection and local action planning.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <Link href="/demo" className="fi-btn fi-btn--primary">Launch demo →</Link>
              <a
                href="https://github.com/BernardUriza/activist-os"
                className="fi-btn fi-btn--ghost"
                target="_blank"
                rel="noopener noreferrer"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="border-t py-10" style={{ borderColor: 'var(--fi-border-soft)' }}>
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-faint">
          <p className="fi-mono">Activist OS · Free Intelligence</p>
          <p>Built for the Band of Agents Hackathon · Regulated &amp; High-Stakes Workflows</p>
        </div>
      </footer>
    </>
  );
}
