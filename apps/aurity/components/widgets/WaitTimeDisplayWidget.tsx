'use client';

import { Timer, User, Check } from 'lucide-react';

interface WaitTimeDisplayWidgetProps {
  estimatedMinutes: number;
  patientsAhead?: number;
}

export function WaitTimeDisplayWidget({
  estimatedMinutes,
  patientsAhead = 3,
}: WaitTimeDisplayWidgetProps) {
  const getTimeColor = () => {
    if (estimatedMinutes <= 10) return 'fi-text-success';
    if (estimatedMinutes <= 20) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getTimeBg = () => {
    if (estimatedMinutes <= 10) return 'from-emerald-950/60 to-green-950/60';
    if (estimatedMinutes <= 20) return 'from-yellow-950/60 to-amber-950/60';
    return 'from-orange-950/60 to-red-950/60';
  };

  return (
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${getTimeBg()} border border-slate-700/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center`}>
      <div className="mb-4 sm:mb-6">
        <Timer className="w-24 h-24 sm:w-32 sm:h-32 lg:w-40 lg:h-40 text-slate-300" strokeWidth={1} aria-hidden="true" />
      </div>

      <p className="text-slate-400 mb-2 sm:mb-4" style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}>
        Tiempo de espera estimado
      </p>

      <div className="flex items-baseline gap-2 sm:gap-4 mb-4 sm:mb-6">
        <span className={`font-black ${getTimeColor()}`} style={{ fontSize: 'clamp(4rem, 15vw, 14rem)' }}>
          {estimatedMinutes}
        </span>
        <span className="text-slate-400 font-bold" style={{ fontSize: 'clamp(1.5rem, 4vw, 4rem)' }}>
          min
        </span>
      </div>

      <div className="fi-flex-gap sm:gap-3 text-slate-400">
        <span
          className="bg-slate-800/60 px-4 sm:px-6 py-2 sm:py-3 rounded-full flex items-center gap-2"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          <User className="w-5 h-5 sm:w-6 sm:h-6" strokeWidth={1.5} aria-hidden="true" />
          {patientsAhead} {patientsAhead === 1 ? 'paciente' : 'pacientes'} antes que usted
        </span>
      </div>

      <p className="fi-text-success/80 mt-6 sm:mt-8 flex items-center justify-center gap-2" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
        <Check className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={2} aria-hidden="true" />
        Le avisaremos cuando sea su turno
      </p>
    </div>
  );
}
