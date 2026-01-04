'use client';

interface DailyTipWidgetProps {
  tip: string;
  category: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
  generatedBy?: 'FI' | 'static';
}

const categoryConfig = {
  nutrition: {
    icon: '🥗',
    label: 'Nutrición',
    color: 'text-green-300',
    bgColor: 'bg-gradient-to-br from-green-950/60 to-emerald-950/40',
    borderColor: 'border-green-600/40',
    accentBg: 'bg-green-500/10',
  },
  exercise: {
    icon: '🏃',
    label: 'Actividad Física',
    color: 'text-blue-300',
    bgColor: 'bg-gradient-to-br from-blue-950/60 to-cyan-950/40',
    borderColor: 'border-blue-600/40',
    accentBg: 'bg-blue-500/10',
  },
  mental_health: {
    icon: '🧠',
    label: 'Salud Mental',
    color: 'text-purple-300',
    bgColor: 'bg-gradient-to-br from-purple-950/60 to-violet-950/40',
    borderColor: 'border-purple-600/40',
    accentBg: 'bg-purple-500/10',
  },
  prevention: {
    icon: '🛡️',
    label: 'Prevención',
    color: 'text-orange-300',
    bgColor: 'bg-gradient-to-br from-orange-950/60 to-amber-950/40',
    borderColor: 'border-orange-600/40',
    accentBg: 'bg-orange-500/10',
  },
};

export function DailyTipWidget({ tip, category, generatedBy = 'static' }: DailyTipWidgetProps) {
  const config = categoryConfig[category];

  return (
    <div className={`h-full flex flex-col ${config.bgColor} border ${config.borderColor} rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8`}>
      <div className="fi-flex-between mb-4 sm:mb-6 flex-shrink-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className={`${config.accentBg} rounded-full p-3 sm:p-4`} style={{ fontSize: 'clamp(2rem, 4vw, 4rem)' }}>
            {config.icon}
          </div>
          <div>
            <h3 className={`font-bold ${config.color}`} style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}>
              Tip del Día
            </h3>
            <p className="text-slate-400" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
              {config.label}
            </p>
          </div>
        </div>
        {generatedBy === 'FI' && (
          <div className="flex items-center gap-2 fi-text-purple bg-purple-500/10 px-3 py-1.5 rounded-full" style={{ fontSize: 'clamp(0.75rem, 1vw, 1rem)' }}>
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 7H7v6h6V7z" />
              <path fillRule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clipRule="evenodd" />
            </svg>
            <span className="hidden sm:inline">Generado por FI</span>
          </div>
        )}
      </div>

      <div className="flex-1 flex items-center justify-center min-h-0 px-4 sm:px-8 lg:px-12">
        <p
          className="text-white text-center leading-relaxed font-medium"
          style={{
            fontSize: tip.length > 150
              ? 'clamp(1rem, 2.5vw, 2rem)'
              : tip.length > 80
              ? 'clamp(1.25rem, 3vw, 2.5rem)'
              : 'clamp(1.5rem, 4vw, 3.5rem)',
            maxWidth: '90%',
          }}
        >
          {tip}
        </p>
      </div>

      <div className="flex-shrink-0 mt-4 pt-4 fi-border-top/30">
        <div className="flex items-center justify-center gap-2 text-slate-500" style={{ fontSize: 'clamp(0.7rem, 1vw, 1rem)' }}>
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span>Consejos de salud • Actualizado diariamente</span>
        </div>
      </div>
    </div>
  );
}
