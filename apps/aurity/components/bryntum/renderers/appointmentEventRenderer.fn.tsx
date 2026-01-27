
/**
 * Bryntum eventRenderer adapter that returns a React element.
 * Keeping this in a .tsx file ensures JSX is compiled correctly.
 */
// Bryntum WebComponent bundle expects a string or DomConfig, not React elements.
// Returning a DomConfig avoids Symbol attribute errors in `_DomSync.syncAttributes`.
// Keep this implementation framework-agnostic.

type EventRecord = {
  name?: string
  patient_name?: string
  reason?: string
  status?: string
  type?: string
  startDate?: Date | string
  endDate?: Date | string
}

const statusToBarClass = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s.includes('cancel')) return 'bg-red-500'
  if (s.includes('noshow') || s.includes('no-show')) return 'bg-orange-500'
  if (s.includes('late')) return 'bg-yellow-500'
  if (s.includes('done') || s.includes('completed')) return 'bg-green-500'
  if (s.includes('in') && s.includes('progress')) return 'bg-blue-500'
  return 'bg-gray-400'
}

const typeToIcon = (type?: string) => {
  const t = (type || '').toLowerCase()
  if (t.includes('check') || t.includes('general')) return 'C' // Consulta
  if (t.includes('follow')) return 'S' // Seguimiento
  if (t.includes('vaccine') || t.includes('shot')) return 'V' // Vacuna
  return 'A' // Cita (Appointment)
}

const formatTime = (d?: Date | string) => {
  if (!d) return ''
  const date = typeof d === 'string' ? new Date(d) : d
  try {
    return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function appointmentEventRenderer({ eventRecord }: { eventRecord: EventRecord }) {
  const patient = eventRecord.patient_name || eventRecord.name || 'Paciente'
  const reason = eventRecord.reason || ''
  const status = eventRecord.status || ''
  const icon = typeToIcon(eventRecord.type)
  const start = formatTime(eventRecord.startDate)
  const end = formatTime(eventRecord.endDate)
  const timeRange = start && end ? `${start} - ${end}` : start || ''

  // DomConfig per Bryntum, children are simple strings/objects only.
  return {
    className:
      'fi-appt-card flex items-center gap-2 rounded-md shadow-sm bg-white/90 dark:bg-neutral-900 text-[11px] leading-tight h-full overflow-hidden',
    children: [
      { tag: 'div', className: `h-full w-1 ${statusToBarClass(status)}` },
      {
        tag: 'div',
        className: 'flex-1 min-w-0 px-2 py-1',
        children: [
          {
            tag: 'div',
            className: 'flex items-center gap-1 font-semibold text-[11px] truncate',
            children: [
              { tag: 'span', className: 'mr-1', html: icon },
              { tag: 'span', className: 'truncate', html: patient },
            ],
          },
          {
            tag: 'div',
            className: 'text-[10px] text-neutral-500 dark:text-neutral-400 truncate',
            html: reason,
          },
        ],
      },
      {
        tag: 'div',
        className: 'px-2 py-1 text-[10px] text-neutral-600 dark:text-neutral-300 whitespace-nowrap',
        html: timeRange,
      },
    ],
  }
}

export default appointmentEventRenderer;
 