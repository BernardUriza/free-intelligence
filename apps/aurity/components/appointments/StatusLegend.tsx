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
    <div className="apt-legend">
      <div className="apt-legend-inner">
        <span className="apt-legend-label">Estado:</span>
        {statuses.map(({ color, label }) => (
          <div key={label} className="fi-flex-gap-sm">
            <span className={`apt-legend-dot ${color}`} />
            <span className="fi-text">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
