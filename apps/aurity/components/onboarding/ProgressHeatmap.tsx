"use client";

/**
 * Progress Heatmap Component - Phase 8 (FI-ONBOARD-008)
 *
 * GitHub contributions-style heatmap showing onboarding progress
 */

interface Phase {
  name: string;
  completed: boolean;
  date: Date;
}

interface ProgressHeatmapProps {
  phases: Phase[];
}

export function ProgressHeatmap({ phases }: ProgressHeatmapProps) {
  /**
   * Get color intensity based on completion
   */
  const getColorClass = (completed: boolean, index: number): string => {
    if (!completed) {
      return 'bg-slate-800/40 border-slate-700/50';
    }

    // Gradient intensity based on order (earlier phases = lighter, later = darker)
    const intensity = Math.floor((index / phases.length) * 4);
    switch (intensity) {
      case 0:
        return 'bg-emerald-900/60 border-emerald-700/60';
      case 1:
        return 'bg-emerald-700/70 border-emerald-600/70';
      case 2:
        return 'bg-emerald-600/80 border-emerald-500/80';
      case 3:
      default:
        return 'bg-emerald-500/90 border-emerald-400/90';
    }
  };

  return (
    <div className="space-y-4">
      {/* Heatmap Grid */}
      <div className="flex justify-center">
        <div className="inline-flex items-center gap-2 p-4 bg-slate-950/40 rounded-xl border border-slate-700/50">
          {phases.map((phase, index) => (
            <div key={phase.name} className="group relative">
              {/* Square */}
              <div
                className={`w-12 h-12 rounded border-2 transition-all hover:scale-110 ${getColorClass(
                  phase.completed,
                  index
                )}`}
              >
                {phase.completed && (
                  <div className="w-full h-full flex items-center justify-center text-emerald-200 text-xl">
                    ✓
                  </div>
                )}
              </div>

              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 shadow-xl whitespace-nowrap">
                  <p className="text-xs font-semibold text-slate-200">{phase.name}</p>
                  <p className="fi-text-xs mt-1">
                    {phase.completed ? '✅ Completed' : '⏳ Pending'}
                  </p>
                  {phase.completed && (
                    <p className="fi-text-xs-muted mt-1">
                      {phase.date.toLocaleDateString('es-MX', {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </p>
                  )}
                </div>
                {/* Arrow */}
                <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-700" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Phase Labels */}
      <div className="flex justify-center">
        <div className="inline-flex items-center gap-2">
          {phases.map((phase) => (
            <div key={phase.name} className="w-12 text-center">
              <p className="fi-text-xs truncate" title={phase.name}>
                {phase.name.split(' ')[0]}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 pt-4 fi-border-top/50">
        <p className="fi-text-xs">Less</p>
        <div className="flex gap-2">
          <div className="w-4 h-4 rounded border-2 bg-slate-800/40 border-slate-700/50" />
          <div className="w-4 h-4 rounded border-2 bg-emerald-900/60 border-emerald-700/60" />
          <div className="w-4 h-4 rounded border-2 bg-emerald-700/70 border-emerald-600/70" />
          <div className="w-4 h-4 rounded border-2 bg-emerald-600/80 border-emerald-500/80" />
          <div className="w-4 h-4 rounded border-2 bg-emerald-500/90 border-emerald-400/90" />
        </div>
        <p className="fi-text-xs">More</p>
      </div>

      {/* Stats */}
      <div className="fi-grid-3 pt-4">
        <div className="text-center">
          <p className="text-2xl font-bold fi-text-success">
            {phases.filter((p) => p.completed).length}
          </p>
          <p className="fi-text-xs mt-1">Completed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-slate-400">
            {phases.filter((p) => !p.completed).length}
          </p>
          <p className="fi-text-xs mt-1">Remaining</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold fi-text-info">
            {Math.round((phases.filter((p) => p.completed).length / phases.length) * 100)}%
          </p>
          <p className="fi-text-xs mt-1">Progress</p>
        </div>
      </div>
    </div>
  );
}
