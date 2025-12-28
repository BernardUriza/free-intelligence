/**
 * Status Legend Component
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Visual legend showing appointment status color codes.
 */

export function StatusLegend() {
  const statuses = [
    { color: 'bg-blue-500', label: 'Programada' },
    { color: 'bg-green-500', label: 'Confirmada' },
    { color: 'bg-teal-500', label: 'Check-in' },
    { color: 'bg-orange-500', label: 'En curso' },
    { color: 'bg-slate-500', label: 'Completada' },
    { color: 'bg-red-500', label: 'Cancelada' },
    { color: 'bg-yellow-500', label: 'No asistió' },
  ];

  return (
    <div className="bg-slate-900/50 fi-border-bottom px-6 py-2">
      <div className="flex items-center gap-6 text-sm">
        <span className="text-slate-500">Estado:</span>
        {statuses.map(({ color, label }) => (
          <div key={label} className="fi-flex-gap-sm">
            <span className={`w-3 h-3 rounded-full ${color}`} />
            <span className="fi-text">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
