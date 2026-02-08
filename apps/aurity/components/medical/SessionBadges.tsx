/**
 * SessionBadges Component
 *
 * Displays Session ID and Job ID badges with copy-to-clipboard functionality.
 *
 * Features:
 * - Session ID badge (UUID format)
 * - Job ID badge (when available)
 * - Copy to clipboard on hover
 * - Truncated display with full copy
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SessionBadgesProps {
  sessionId: string | null;
  jobId: string | null;
  copiedId: string | null;
  onCopy: (id: string, type: string) => void;
}

export function SessionBadges({
  sessionId,
  jobId,
  copiedId,
  onCopy,
}: SessionBadgesProps) {
  if (!sessionId && !jobId) return null;

  return (
    <div className="absolute top-0 right-0 z-10">
      <div className="med-session-badge">
        <div className="flex flex-col gap-1">
          {sessionId && (
            <div className="flex items-center gap-2 group">
              <span className="fi-fi-text-xs-medium">Session:</span>
              <code className="text-xs font-mono fi-text-success tracking-tight">
                {sessionId.slice(0, 8)}...
              </code>
              <Button
                onClick={() => onCopy(sessionId, 'session')}
                variant="ghost"
                size="sm"
                icon={copiedId === 'session' ? Check : Copy}
                className={`opacity-0 group-hover:opacity-100 transition-opacity p-0.5 ${copiedId === 'session' ? 'fi-text-green' : 'text-slate-400'}`}
                title="Copy full Session ID"
                aria-label="Copy Session ID"
              />
            </div>
          )}
          {jobId && (
            <div className="flex items-center gap-2 group">
              <span className="fi-fi-text-xs-medium">Job:</span>
              <code className="text-xs font-mono fi-text-info tracking-tight">
                {jobId.slice(0, 8)}...
              </code>
              <Button
                onClick={() => onCopy(jobId, 'job')}
                variant="ghost"
                size="sm"
                icon={copiedId === 'job' ? Check : Copy}
                className={`opacity-0 group-hover:opacity-100 transition-opacity p-0.5 ${copiedId === 'job' ? 'fi-text-green' : 'text-slate-400'}`}
                title="Copy full Job ID"
                aria-label="Copy Job ID"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
