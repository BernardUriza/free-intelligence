'use client';

/**
 * og118 agentic chat — the glass-box surface.
 *
 * og118 supplies only the app-specific pieces: the TRANSPORT (useOg118Agent),
 * the access-token banner, branding/copy, and the start screen. The reusable
 * conversation machinery — visible transcript, optimistic user message,
 * assistant fold, live AgentPanel, new-conversation — lives in the framework
 * (fi-glass `useAgentConversation` + `AgentConversationSurface`). DD-002-LESSON:
 * the consumer consumes the primitive; it does not re-implement it.
 */

import { useState } from 'react';
import { AgentConversationSurface, useAgentConversation } from 'fi-glass/agent';
import { useOg118Agent } from '@/lib/useOg118Agent';
import { getToken, setToken, AUTH401 } from '@/lib/og118Token';
import { Og118StartScreen } from './Og118StartScreen';

export function Og118AgentChat() {
  const agent = useOg118Agent();
  const conversation = useAgentConversation(agent);
  const [tokenInput, setTokenInput] = useState(() => getToken() ?? '');
  const { turn } = conversation;

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

  const authBanner = needsAuth ? (
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
          onKeyDown={(e) => {
            if (e.key === 'Enter') saveToken();
          }}
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
  ) : null;

  return (
    <AgentConversationSurface
      conversation={conversation}
      composerPlaceholder="Pregúntale a og118 (verás su plan en vivo)…"
      newChatLabel="Nuevo chat"
      emptyState={<Og118StartScreen />}
      aboveComposer={authBanner}
      composerAreaClassName="og-composer-area"
      composerTextareaClassName="og-composer-textarea"
      showCopyAction
    />
  );
}
