/**
 * RecordingControls Component
 *
 * Main recording button with pause/resume functionality for Medical AI.
 * Uses shared recording primitives from @/components/recording.
 *
 * Features:
 * - Start/Pause/Resume recording with clear visual states
 * - State machine pattern for predictable behavior
 * - Accessibility: ring indicator for colorblind users
 * - Debounce protection (prevents double-click)
 *
 * Refactored: 2025-12-11 - Uses shared recording primitives
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import { Mic, Pause, Play, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import {
  RecordingButton,
  PulseRings,
  RecordingTimer,
  StatusText,
  type RecordingStateType,
  COLOR_THEMES,
  STATUS_TEXT_ES,
} from '@/components/recording';

// =============================================================================
// Types
// =============================================================================

interface RecordingControlsProps {
  isRecording: boolean;
  isPaused: boolean;
  isProcessing: boolean;
  isFinalized: boolean;
  recordingTime: number;
  onStart: () => void | Promise<void>;
  onPause: () => void | Promise<void>;
  onResume: () => void | Promise<void>;
}

type TransitionAction = 'starting' | 'pausing' | 'resuming' | null;

// =============================================================================
// State Derivation
// =============================================================================

function deriveState(
  isRecording: boolean,
  isPaused: boolean,
  isProcessing: boolean,
  isFinalized: boolean,
  transitionAction: TransitionAction
): RecordingStateType {
  if (isFinalized) return 'finalized';
  if (transitionAction === 'starting') return 'starting';
  if (transitionAction === 'pausing') return 'pausing';
  if (transitionAction === 'resuming') return 'resuming';
  if (isProcessing) return 'processing';
  if (isRecording) return 'recording';
  if (isPaused) return 'paused';
  return 'idle';
}

// =============================================================================
// Configuration
// =============================================================================

const STATE_ICONS: Record<RecordingStateType, LucideIcon> = {
  idle: Mic,
  starting: Loader2,
  recording: Pause,
  pausing: Loader2,
  paused: Play,
  resuming: Loader2,
  processing: Loader2,
  stopping: Loader2,
  finalized: Mic,
};

const LOADING_STATES: RecordingStateType[] = ['starting', 'pausing', 'resuming', 'processing', 'stopping'];
const PULSE_STATES: RecordingStateType[] = ['recording'];
const TIME_VISIBLE_STATES: RecordingStateType[] = ['recording', 'paused', 'pausing', 'resuming'];

// Accessibility: states that need extra visual distinction
const BORDER_STYLES: Partial<Record<RecordingStateType, string>> = {
  paused: 'ring-4 ring-blue-300/70 ring-offset-2 ring-offset-slate-800',
};

// Animation styles
const ANIMATE_STYLES: Partial<Record<RecordingStateType, string>> = {
  recording: 'animate-heartbeat',
};

// Status text customization
const STATUS_OVERRIDE: Partial<Record<RecordingStateType, string>> = {
  idle: 'Presiona para comenzar a grabar',
  recording: 'Grabando... (Click para pausar)',
  paused: 'Pausado (Click para reanudar)',
  finalized: '✅ Sesión completada',
};

// =============================================================================
// Aria Labels
// =============================================================================

function getAriaLabel(state: RecordingStateType): string {
  switch (state) {
    case 'idle': return 'Iniciar grabación';
    case 'recording': return 'Pausar grabación';
    case 'paused': return 'Reanudar grabación';
    case 'finalized': return 'Sesión finalizada';
    default: return 'Procesando...';
  }
}

// =============================================================================
// Main Component
// =============================================================================

export function RecordingControls({
  isRecording,
  isPaused,
  isProcessing,
  isFinalized,
  recordingTime,
  onStart,
  onPause,
  onResume,
}: RecordingControlsProps) {
  const [transitionAction, setTransitionAction] = useState<TransitionAction>(null);

  // Derive current state from all inputs
  const state = useMemo(
    () => deriveState(isRecording, isPaused, isProcessing, isFinalized, transitionAction),
    [isRecording, isPaused, isProcessing, isFinalized, transitionAction]
  );

  const isTransitioning = transitionAction !== null;
  const isDisabled = isProcessing || isTransitioning || isFinalized;
  const showTime = TIME_VISIBLE_STATES.includes(state);
  const showPulse = PULSE_STATES.includes(state);
  const isLoading = LOADING_STATES.includes(state);

  const handleClick = useCallback(async () => {
    if (isFinalized) {
      console.warn('[RecordingControls] Session finalized - recording not allowed');
      return;
    }

    if (isTransitioning || isProcessing) {
      console.warn('[RecordingControls] Ignoring click - already transitioning');
      return;
    }

    const action: TransitionAction = isPaused ? 'resuming' : isRecording ? 'pausing' : 'starting';
    const handler = isPaused ? onResume : isRecording ? onPause : onStart;

    setTransitionAction(action);
    const startTime = Date.now();

    try {
      await handler();
      const elapsed = Date.now() - startTime;
      const minWait = 150;
      if (elapsed < minWait) {
        setTimeout(() => setTransitionAction(null), minWait - elapsed);
      } else {
        setTransitionAction(null);
      }
    } catch (error) {
      console.error('[RecordingControls] Action failed:', error);
      setTransitionAction(null);
    }
  }, [isFinalized, isTransitioning, isProcessing, isPaused, isRecording, onStart, onPause, onResume]);

  // Get configuration for current state
  const colors = COLOR_THEMES.medical;
  const statusText = STATUS_OVERRIDE[state] || STATUS_TEXT_ES[state];
  const statusColor = state === 'finalized' ? 'fi-text-green' :
                      isLoading ? 'fi-text-info' :
                      state === 'recording' ? 'text-yellow-400' :
                      state === 'paused' ? 'fi-text-primary' :
                      'text-slate-400';

  return (
    <div className="fi-card-xl-lg">
      <div className="fi-stack-center-lg">
        {/* Main Button with Pulse Rings */}
        <div className="relative">
          <RecordingButton
            size="xl"
            bgColor={colors[state]}
            icon={STATE_ICONS[state]}
            iconSpin={isLoading}
            disabled={isDisabled}
            onClick={handleClick}
            ariaLabel={getAriaLabel(state)}
            borderStyle={BORDER_STYLES[state]}
            animate={ANIMATE_STYLES[state]}
            className="relative z-10"
          />
          {showPulse && (
            <PulseRings
              style="ping"
              color="yellow-500"
            />
          )}
        </div>

        {/* Recording Time */}
        <RecordingTimer
          time={recordingTime}
          visible={showTime}
          size="lg"
          textColor="text-white"
        />

        {/* Status Text */}
        <div className="min-h-[28px]">
          <StatusText
            text={statusText}
            color={statusColor}
            showLoader={isLoading}
            animate={isLoading}
          />
        </div>
      </div>
    </div>
  );
}
