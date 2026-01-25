'use client';

import { useEffect, useState, useRef } from 'react';
import { ArrowUp, Pause, ArrowDown, Heart } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export function BreathingExerciseWidget() {
  const [phase, setPhase] = useState<'inhale' | 'hold' | 'exhale'>('inhale');
  const [count, setCount] = useState(4);
  const phaseRef = useRef<'inhale' | 'hold' | 'exhale'>(phase);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCount(prev => {
        if (prev === 1) {
          setPhase(current => {
            if (current === 'inhale') return 'hold';
            if (current === 'hold') return 'exhale';
            return 'inhale';
          });
          return phaseRef.current === 'hold' ? 7 : 4;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const phaseConfig: Record<'inhale' | 'hold' | 'exhale', {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    glowColor: string;
    icon: LucideIcon;
  }> = {
    inhale: {
      label: 'Inhala profundamente',
      color: 'text-cyan-300',
      bgColor: 'bg-cyan-500/20',
      borderColor: 'border-cyan-500',
      glowColor: 'shadow-cyan-500/30',
      icon: ArrowUp,
    },
    hold: {
      label: 'Sostén la respiración',
      color: 'text-purple-300',
      bgColor: 'bg-purple-500/20',
      borderColor: 'border-purple-500',
      glowColor: 'shadow-purple-500/30',
      icon: Pause,
    },
    exhale: {
      label: 'Exhala lentamente',
      color: 'text-orange-300',
      bgColor: 'bg-orange-500/20',
      borderColor: 'border-orange-500',
      glowColor: 'shadow-orange-500/30',
      icon: ArrowDown,
    },
  };

  const config = phaseConfig[phase];

  return (
    <div className="h-full flex flex-col items-center justify-center bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      <div className="text-center mb-4 sm:mb-6 lg:mb-8 flex-shrink-0">
        <div className="text-purple-400 mb-2">
          <Heart className="w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16 mx-auto" strokeWidth={1.5} />
        </div>
        <h3 className="font-bold text-white" style={{ fontSize: 'clamp(1.5rem, 3vw, 3rem)' }}>
          Ejercicio de Respiración
        </h3>
        <p className="text-slate-400 mt-1" style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}>
          Técnica 4-7-8 para reducir ansiedad
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center w-full min-h-0">
        <div
          className={`
            relative rounded-full
            ${config.bgColor} ${config.borderColor} border-4 sm:border-6 lg:border-8
            flex items-center justify-center
            transition-all duration-1000 ease-in-out
            shadow-2xl ${config.glowColor}
            ${phase === 'inhale' ? 'scale-110' : phase === 'exhale' ? 'scale-90' : 'scale-100'}
          `}
          style={{ width: 'min(50vh, 50vw, 400px)', height: 'min(50vh, 50vw, 400px)' }}
        >
          <div className="text-center">
            <div className={`font-bold ${config.color} leading-none`} style={{ fontSize: 'clamp(4rem, 15vw, 12rem)' }}>
              {count}
            </div>
            <div className={`${config.color} mt-2 flex justify-center`}>
              <config.icon style={{ width: 'clamp(2rem, 6vw, 5rem)', height: 'clamp(2rem, 6vw, 5rem)' }} strokeWidth={2} />
            </div>
          </div>
        </div>
      </div>

      <div className="text-center mt-4 sm:mt-6 lg:mt-8 flex-shrink-0">
        <p className={`font-semibold ${config.color}`} style={{ fontSize: 'clamp(1.25rem, 3vw, 3rem)' }}>
          {config.label}
        </p>
      </div>
    </div>
  );
}
