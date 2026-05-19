/**
 * VoiceMicButton Component
 *
 * Compact microphone button for chat with VAD (Voice Activity Detection).
 * Uses shared recording primitives from @/components/recording.
 *
 * Features:
 * - VAD rings that respond to audio level
 * - Color feedback: green (voice), red (silent)
 * - Compact design for chat toolbar
 * - Recording timer display
 *
 * Refactored: 2025-12-11 - Uses shared recording primitives
 */

'use client';

import { Mic, Square, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

import {
  RecordingButton,
  PulseRings,
  RecordingTimer,
  type RecordingStateType,
} from '@/components/recording';

// =============================================================================
// Types
// =============================================================================

interface VoiceMicButtonProps {
  isRecording: boolean;
  isTranscribing: boolean;
  audioLevel: number; // 0-255 (from Web Audio API)
  isSilent: boolean;
  recordingTime: number; // seconds
  onStart: () => void;
  onStop: () => void;
  className?: string;
}

// =============================================================================
// State Derivation
// =============================================================================

function deriveState(
  isRecording: boolean,
  isTranscribing: boolean
): RecordingStateType {
  if (isTranscribing && !isRecording) return 'processing';
  if (isRecording) return 'recording';
  return 'idle';
}

// =============================================================================
// Custom Chat Color Theme (VAD-aware)
// =============================================================================

function getButtonColor(state: RecordingStateType, isSilent: boolean): string {
  if (state === 'recording') {
    return isSilent
      ? 'bg-red-500 hover:bg-red-600 text-white'
      : 'bg-green-500 hover:bg-green-600 text-white';
  }
  if (state === 'processing') {
    return 'bg-blue-500 text-white';
  }
  return 'bg-gray-200 hover:bg-gray-300 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200';
}

// =============================================================================
// Main Component
// =============================================================================

export function VoiceMicButton({
  isRecording,
  isTranscribing,
  audioLevel,
  isSilent,
  recordingTime,
  onStart,
  onStop,
  className = '',
}: VoiceMicButtonProps) {
  const state = deriveState(isRecording, isTranscribing);
  const isDisabled = isTranscribing && !isRecording;

  const handleClick = () => {
    if (isRecording) {
      onStop();
    } else if (!isTranscribing) {
      onStart();
    }
  };

  // Icon selection
  const icon = isTranscribing ? Loader2 : isRecording ? Square : Mic;
  const iconColor = state === 'idle' ? 'text-gray-700 dark:text-gray-200' : 'text-white';

  return (
    <div className={`relative inline-flex items-center gap-3 ${className}`}>
      {/* Button Container with VAD Rings */}
      <div className="relative">
        {/* VAD Pulse Rings */}
        {isRecording && (
          <PulseRings
            style="vad"
            audioLevel={audioLevel}
            isSilent={isSilent}
          />
        )}

        {/* Main Button */}
        <motion.div
          animate={{
            scale: isRecording && !isSilent ? [1, 1.05, 1] : 1,
          }}
          transition={{
            duration: 0.6,
            repeat: isRecording && !isSilent ? Infinity : 0,
            ease: 'easeInOut',
          }}
        >
          <RecordingButton
            size="md"
            bgColor={getButtonColor(state, isSilent)}
            icon={icon}
            iconSpin={isTranscribing && !isRecording}
            iconColor={iconColor}
            disabled={isDisabled}
            onClick={handleClick}
            ariaLabel={isRecording ? 'Detener grabación' : 'Iniciar grabación de voz'}
            className="relative z-10"
          />
        </motion.div>
      </div>

      {/* Recording Timer with Dot */}
      {isRecording && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
        >
          <RecordingTimer
            time={recordingTime}
            size="sm"
            showDot
            textColor="text-gray-700 dark:text-gray-300"
          />
        </motion.div>
      )}

      {/* Transcribing Indicator */}
      {isTranscribing && !isRecording && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-blue-600 dark:fi-text-primary font-medium"
        >
          Transcribiendo...
        </motion.div>
      )}
    </div>
  );
}
