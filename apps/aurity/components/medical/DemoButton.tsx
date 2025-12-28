/**
 * DemoButton Component
 *
 * Button to play/pause/resume demo audio consultation.
 *
 * Features:
 * - Play/Pause/Resume states with icons
 * - Visual feedback (color changes)
 * - Disabled state during processing
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { Play, Pause } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DemoButtonProps {
  isDemoPlaying: boolean;
  isDemoPaused: boolean;
  isProcessing: boolean;
  onToggle: () => void;
}

export function DemoButton({
  isDemoPlaying,
  isDemoPaused,
  isProcessing,
  onToggle,
}: DemoButtonProps) {
  // Determine icon and label based on state
  const Icon = isDemoPlaying && !isDemoPaused ? Pause : Play;
  const label = isDemoPaused ? 'Continuar' : isDemoPlaying ? 'Pausar' : 'Demo';
  const title = isDemoPaused
    ? 'Continuar reproducción'
    : isDemoPlaying
    ? 'Pausar demo'
    : 'Reproducir consulta de demostración';

  return (
    <div className="absolute top-0 left-0 z-10">
      <Button
        onClick={onToggle}
        disabled={isProcessing}
        variant="purple"
        icon={Icon}
        title={title}
        className={
          isDemoPaused
            ? 'bg-amber-600 hover:bg-amber-700'
            : isDemoPlaying && !isDemoPaused
            ? 'bg-purple-500'
            : ''
        }
      >
        {label}
      </Button>
    </div>
  );
}
