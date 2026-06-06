'use client';

/**
 * og118 agentic chat — the glass-box surface. Uses useOg118Agent (AgentHook) +
 * fi-glass/agent's AgentPanel to render the live plan → steps → tool-trace, then
 * the answer. This is where Berkelio's reducer (applyAgentEvent) is re-validated
 * against the REAL fi-runner event mix.
 */

import { useState } from 'react';
import { Composer } from 'fi-glass/composer';
import { MessageContent } from 'fi-glass/messages';
import { AgentPanel } from 'fi-glass/agent';
import { useOg118Agent } from '@/lib/useOg118Agent';
import { getToken, setToken, AUTH401 } from '@/lib/og118Token';
import { Og118StartScreen } from './Og118StartScreen';

export function Og118AgentChat() {
  const agent = useOg118Agent();
  const [input, setInput] = useState('');
  const [tokenInput, setTokenInput] = useState(() => getToken() ?? '');
  const { turn } = agent;

  // The backend returned 401 (gated cloud, no/invalid token). Surface a usable
  // affordance to paste the access token at runtime (it lives only in this
  // browser's localStorage — never in the bundle).
  const needsAuth = turn.status === 'error' && (turn.errorMessage ?? '').startsWith(AUTH401);

  const saveToken = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setToken(t);
    agent.reset?.(); // clear the error banner; the user re-sends with the token set
  };

  const send = () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    void agent.send(text);
  };

  const idle = turn.status === 'thinking' && !turn.plan && turn.steps.length === 0 && !turn.text;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', maxWidth: 760, margin: '0 auto' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1rem' }}>
        {idle ? (
          <Og118StartScreen />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Glass-box: plan checklist + live step/tool trace + sources */}
            <AgentPanel turn={turn} />

            {/* The answer */}
            {turn.text && (
              <div style={{ paddingTop: '0.5rem' }}>
                <MessageContent isUser={false} content={turn.text} isStreaming={agent.isStreaming} />
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {needsAuth && (
          <div
            style={{
              marginBottom: '0.75rem',
              padding: '0.75rem',
              borderRadius: 10,
              border: '1px solid rgba(248,113,113,0.35)',
              background: 'rgba(248,113,113,0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            <span style={{ color: '#fca5a5', fontSize: '0.85rem' }}>
              Acceso restringido — pega tu token de og118 para continuar.
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') saveToken(); }}
                placeholder="og118 access token"
                style={{
                  flex: 1,
                  padding: '0.5rem 0.75rem',
                  borderRadius: 8,
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(15,23,42,0.6)',
                  color: '#e2e8f0',
                  fontSize: '0.85rem',
                }}
              />
              <button
                onClick={saveToken}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: 8,
                  border: '1px solid var(--og-accent, #34d399)',
                  background: 'transparent',
                  color: 'var(--og-accent, #34d399)',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                Guardar
              </button>
            </div>
          </div>
        )}
        <Composer
          message={input}
          loading={agent.isStreaming}
          placeholder="Pregúntale a og118 (verás su plan en vivo)…"
          onMessageChange={setInput}
          onSend={send}
          areaClassName="og-composer-area"
          textareaClassName="og-composer-textarea"
        />
      </div>
    </div>
  );
}
