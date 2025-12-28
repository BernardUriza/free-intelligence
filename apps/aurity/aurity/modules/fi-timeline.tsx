/**
 * FI Timeline Module - Stub
 *
 * Minimal implementation to unblock build.
 * This module was referenced but never fully implemented.
 */

import React from 'react';
import { Button } from '@/components/ui/button';

export interface SessionHeaderData {
  metadata: {
    session_id: string;
    created_at: string;
    thread_id?: string;
    owner_hash?: string;
    is_persisted: boolean;
    last_active: string;
    interaction_count: number;
  };
  timespan: {
    start?: string;
    end?: string;
    duration_ms?: number;
    duration_human: string;
  };
  size: {
    interaction_count: number;
    total_tokens: number;
    total_chars: number;
    total_prompts_chars: number;
    total_responses_chars: number;
  };
  policy_badges?: {
    hash_verified: string;
    policy_compliant: string;
    redaction_applied: string;
    audit_logged: string;
  };
}

interface SessionHeaderProps {
  session: SessionHeaderData | null;
  sticky?: boolean;
  onRefresh?: () => void;
  onExport?: () => void;
}

export const SessionHeader: React.FC<SessionHeaderProps> = ({ session, sticky = false, onRefresh, onExport }) => {
  // Guard against undefined/null session
  if (!session || !session.metadata) {
    return (
      <div className={`bg-slate-800 p-4 rounded-lg mb-4 ${sticky ? 'sticky top-0 z-20' : ''}`}>
        <h2 className="fi-title-xl mb-2">Loading session...</h2>
      </div>
    );
  }

  return (
    <div className={`bg-slate-800 p-4 rounded-lg mb-4 fi-border-bottom ${sticky ? 'sticky top-0 z-20 backdrop-blur' : ''}`}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="fi-title-xl mb-2">
            Session: {session.metadata.session_id.substring(0, 8)}...
          </h2>
          <p className="fi-text text-sm">
            Created: {new Date(session.metadata.created_at).toLocaleString()}
          </p>
          {session.timespan && (
            <p className="fi-text text-sm">
              Duration: {session.timespan.duration_human} · {session.size.interaction_count} interactions
            </p>
          )}
        </div>

        {(onRefresh || onExport) && (
          <div className="flex items-center gap-2">
            {onRefresh && (
              <Button onClick={onRefresh} className="px-3 py-1.5 rounded-lg text-sm" variant="ghost" size="sm" type="button">↻ Refresh</Button>
            )}
            {onExport && (
              <Button onClick={onExport} className="px-3 py-1.5 rounded-lg text-sm" variant="secondary" size="sm" type="button">⇣ Export</Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export function generateMockSessionHeader(): SessionHeaderData {
  return {
    metadata: {
      session_id: 'session_20251115_000000',
      created_at: new Date().toISOString(),
      thread_id: 'thread_mock_001',
      owner_hash: 'mock_hash',
      is_persisted: true,
      last_active: new Date().toISOString(),
      interaction_count: 5,
    },
    timespan: {
      start: new Date().toISOString(),
      end: new Date().toISOString(),
      duration_ms: 60000,
      duration_human: '1m',
    },
    size: {
      interaction_count: 5,
      total_tokens: 1000,
      total_chars: 5000,
      total_prompts_chars: 2000,
      total_responses_chars: 3000,
    },
    policy_badges: {
      hash_verified: 'OK',
      policy_compliant: 'OK',
      redaction_applied: 'N/A',
      audit_logged: 'OK',
    },
  };
}

export function generateMockSessionHeaderWithStatus(
  hashStatus: string,
  policyStatus: string,
  redactionStatus: string,
  auditStatus: string
): SessionHeaderData {
  const data = generateMockSessionHeader();
  return {
    ...data,
    policy_badges: {
      hash_verified: hashStatus,
      policy_compliant: policyStatus,
      redaction_applied: redactionStatus,
      audit_logged: auditStatus,
    },
  };
}
