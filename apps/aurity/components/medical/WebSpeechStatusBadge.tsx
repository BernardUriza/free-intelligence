'use client';

/**
 * WebSpeechStatusBadge - Visual indicator for WebSpeech API status
 *
 * Extracted from ConversationCapture during refactoring.
 * Shows ON/OFF status and interim transcription preview.
 */

interface WebSpeechStatusBadgeProps {
  isSupported: boolean;
  isActive: boolean;
  interimText?: string;
}

export function WebSpeechStatusBadge({
  isSupported,
  isActive,
  interimText,
}: WebSpeechStatusBadgeProps) {
  if (!isSupported) return null;

  return (
    <div className="fi-flex-center gap-2">
      <div className={isActive ? 'fi-status-badge-active' : 'fi-status-badge-inactive'}>
        <span className="fi-flex-gap-sm">
          <span className={isActive ? 'fi-status-dot-active' : 'fi-status-dot-inactive'} />
          WebSpeech {isActive ? 'ON' : 'OFF'}
        </span>
      </div>
      {interimText && (
        <div className="fi-interim-badge">
          &ldquo;{interimText}...&rdquo;
        </div>
      )}
    </div>
  );
}
