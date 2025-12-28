/**
 * PulseRings - Animated Ring Effects for Recording
 *
 * Provides visual feedback during recording with multiple animation styles:
 * - ping: Simple Tailwind ping animation
 * - rings: Multiple concentric rings with staggered timing
 * - vad: Voice Activity Detection responsive rings
 *
 * Used by: RecordingControls, VoiceMicButton
 */

'use client';

import { motion } from 'framer-motion';
import type { PulseStyle } from './types';

export interface PulseRingsProps {
  /** Animation style */
  style: PulseStyle;
  /** Ring color (Tailwind class like 'yellow-500') */
  color?: string;
  /** Audio level 0-255 for VAD style */
  audioLevel?: number;
  /** Whether audio is silent (for VAD color switching) */
  isSilent?: boolean;
  /** Additional container classes */
  className?: string;
}

/**
 * Simple CSS ping animation (Tailwind)
 */
function PingRings({ color = 'yellow-500' }: { color?: string }) {
  return (
    <>
      <div
        className={`absolute inset-0 rounded-full bg-${color} animate-ping opacity-30 pointer-events-none`}
      />
      <div
        className={`absolute inset-0 rounded-full bg-${color} opacity-20 pointer-events-none`}
        style={{ animation: 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}
      />
    </>
  );
}

/**
 * Multiple concentric rings with staggered timing
 */
function ConcentricRings({ color = 'yellow-500' }: { color?: string }) {
  const rings = [
    { scale: 1.3, opacity: 0.4, delay: 0 },
    { scale: 1.5, opacity: 0.3, delay: 0.2 },
    { scale: 1.7, opacity: 0.2, delay: 0.4 },
  ];

  return (
    <>
      {rings.map((ring, i) => (
        <motion.div
          key={i}
          className={`absolute inset-0 rounded-full border-2 border-${color} pointer-events-none`}
          initial={{ scale: 1, opacity: ring.opacity }}
          animate={{
            scale: [1, ring.scale, 1],
            opacity: [ring.opacity, ring.opacity * 0.5, ring.opacity],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: ring.delay,
          }}
        />
      ))}
    </>
  );
}

/**
 * VAD (Voice Activity Detection) responsive rings
 * Animación REACTIVA: Los anillos se expanden/contraen AL RITMO de la voz
 *
 * Mapeo audioLevel (0-255) a escala:
 * - Silencio (0-20):      scale = 1.0 (sin expansión)
 * - Voz débil (21-80):    scale = 1.1-1.3
 * - Voz normal (81-150):  scale = 1.3-1.6
 * - Voz fuerte (151-255): scale = 1.6-2.0
 */
function VADRings({
  audioLevel = 0,
  isSilent = true,
}: {
  audioLevel?: number;
  isSilent?: boolean;
}) {
  // Mapeo mejorado: audio level → expansión natural
  // Menos agresivo en silencio, más expresivo en voz fuerte
  const audioScale = !isSilent
    ? Math.max(1, 1 + (audioLevel / 255) * 1.0) // 0-255 → 1.0-2.0
    : 1;

  // Color: green when voice, red when silent
  const ringColor = isSilent ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)';

  // Configuración de anillos concéntricos con opacidad escalonada
  const rings = [
    { baseScale: 1.2, opacityBase: 0.6 },
    { baseScale: 1.4, opacityBase: 0.4 },
    { baseScale: 1.6, opacityBase: 0.2 },
  ];

  return (
    <>
      {rings.map((ring, i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-full border-2 pointer-events-none"
          style={{ borderColor: ringColor }}
          animate={{
            scale: audioScale * ring.baseScale,
            opacity: ring.opacityBase,
          }}
          transition={{
            duration: 0.2,  // Transición suave pero rápida para seguir el ritmo
            ease: 'easeOut',
          }}
        />
      ))}
    </>
  );
}

export function PulseRings({
  style,
  color = 'yellow-500',
  audioLevel = 0,
  isSilent = true,
  className = '',
}: PulseRingsProps) {
  if (style === 'none') return null;

  return (
    <div className={`absolute inset-0 ${className}`}>
      {style === 'ping' && <PingRings color={color} />}
      {style === 'rings' && <ConcentricRings color={color} />}
      {style === 'vad' && <VADRings audioLevel={audioLevel} isSilent={isSilent} />}
    </div>
  );
}
