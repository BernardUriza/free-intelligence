'use client';

interface Og118VoiceErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export function Og118VoiceErrorBanner({ message, onDismiss }: Og118VoiceErrorBannerProps) {
  return (
    <div className="og-voice-error-banner" data-ref="og118-voice-error-banner">
      <span className="og-voice-error-text">{message}</span>
      <button
        className="og-voice-error-dismiss"
        onClick={onDismiss}
        aria-label="Descartar error de voz"
        data-ref="og118-voice-error-dismiss"
      >
        ×
      </button>
    </div>
  );
}
