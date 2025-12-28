/**
 * AudioConsentBanner - First-click tooltip for audio permission
 *
 * Shows on first SpeakButton click:
 * - "Audio playback enabled. Click allow if prompted."
 * - Auto-dismisses after 5 seconds
 * - Persists consent in localStorage: audio_consent_given
 *
 * Explicit consent requirement aligns with AURITY's zero-trust principle
 * and HIPAA compliance (no autoplay without user gesture).
 *
 * @module AudioConsentBanner
 */

'use client';

import { useState, useEffect } from 'react';
import { Volume2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function AudioConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consentGiven = localStorage.getItem('audio_consent_given');
    if (!consentGiven) {
      // Listen for first audio request
      const handleFirstAudio = () => {
        setVisible(true);
        localStorage.setItem('audio_consent_given', 'true');
        // Auto-dismiss after 5 seconds
        setTimeout(() => setVisible(false), 5000);
      };

      window.addEventListener('audio:first-request', handleFirstAudio);
      return () => window.removeEventListener('audio:first-request', handleFirstAudio);
    }
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 max-w-md mx-auto">
      <div
        className="
        bg-purple-900/95 backdrop-blur-sm
        border border-purple-500/50
        rounded-lg shadow-xl
        p-4
        animate-slide-up
      "
      >
        <div className="flex items-start gap-3">
          <Volume2 className="w-5 h-5 text-purple-300 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-white text-sm font-medium">Audio playback enabled</p>
            <p className="text-purple-200 text-xs mt-1">
              Click allow if your browser prompts for permission. Audio will play automatically.
            </p>
          </div>
          <Button
            onClick={() => setVisible(false)}
            variant="ghost"
            size="sm"
            icon={X}
            className="text-purple-300 hover:text-white"
            aria-label="Dismiss"
          />
        </div>
      </div>
    </div>
  );
}
