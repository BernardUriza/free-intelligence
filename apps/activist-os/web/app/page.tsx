'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getHealthFull, type HealthFull } from '@/lib/api';

type ApiState =
  | { status: 'loading' }
  | { status: 'ok'; data: HealthFull }
  | { status: 'error'; message: string };

export default function Home() {
  const [api, setApi] = useState<ApiState>({ status: 'loading' });

  useEffect(() => {
    getHealthFull()
      .then(data => setApi({ status: 'ok', data }))
      .catch(err => setApi({ status: 'error', message: String(err) }));
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <p className="font-mono text-xs tracking-widest uppercase mb-3" style={{ color: 'var(--fi-faint)' }}>
          Regulated &amp; High-Stakes Workflows
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight mb-2">Activist OS</h1>
        <p style={{ color: 'var(--fi-muted)' }}>
          Safe, evidence-backed civic advocacy workflows.
        </p>
      </div>

      {/* API status panel */}
      <div
        className="rounded-2xl p-6 w-full max-w-sm font-mono text-sm"
        style={{
          background: 'var(--fi-surface)',
          border: '1px solid var(--fi-border)',
          backdropFilter: 'blur(20px)',
        }}
      >
        <p className="text-xs tracking-widest uppercase mb-3" style={{ color: 'var(--fi-faint)' }}>
          API status
        </p>
        {api.status === 'loading' && (
          <p style={{ color: 'var(--fi-muted)' }}>Connecting to :8000…</p>
        )}
        {api.status === 'ok' && (
          <div className="space-y-1">
            <p style={{ color: 'var(--fi-approved)' }}>● API connected</p>
            <p style={{ color: 'var(--fi-muted)' }}>transport: {api.data.transport}</p>
            <p style={{ color: 'var(--fi-muted)' }}>active runs: {api.data.active_runs}</p>
          </div>
        )}
        {api.status === 'error' && (
          <div className="space-y-1">
            <p style={{ color: 'var(--fi-veto)' }}>● API unreachable</p>
            <p className="text-xs break-all" style={{ color: 'var(--fi-faint)' }}>
              {api.message}
            </p>
            <p className="text-xs mt-2" style={{ color: 'var(--fi-faint)' }}>
              Run: <code>make dev</code> from activist-os/api
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex gap-4 text-sm font-mono">
        <Link
          href="/demo"
          className="px-4 py-2 rounded-lg transition-colors"
          style={{ background: 'var(--fi-accent)', color: '#fff' }}
        >
          Coordination demo →
        </Link>
        <Link
          href="/checklist"
          className="px-4 py-2 rounded-lg transition-colors"
          style={{ background: 'var(--fi-surface)', border: '1px solid var(--fi-border)', color: 'var(--fi-text)' }}
        >
          Checklist
        </Link>
      </nav>
    </main>
  );
}
