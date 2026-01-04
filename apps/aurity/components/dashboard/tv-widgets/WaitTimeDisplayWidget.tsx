'use client';

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
      <div className="mb-4 sm:mb-6" style={{ fontSize: 'clamp(4rem, 10vw, 10rem)' }}>
        ⏱️
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
          className="bg-slate-800/60 px-4 sm:px-6 py-2 sm:py-3 rounded-full"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          👤 {patientsAhead} {patientsAhead === 1 ? 'paciente' : 'pacientes'} antes que usted
        </span>
      </div>

      <p className="fi-text-success/80 mt-6 sm:mt-8" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
        ✓ Le avisaremos cuando sea su turno
      </p>
    </div>
  );
}
