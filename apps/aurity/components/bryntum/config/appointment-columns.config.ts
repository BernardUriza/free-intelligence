/**
 * Appointments Columns Configuration
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Column definitions for medical appointments scheduler.
 * Shows doctor information as resource rows.
 */

// Column type is defined inline since BryntumColumn export might not be available yet
// Will use any for renderer callback which is valid for Bryntum API

/**
 * Appointments Scheduler Columns
 * 
 * @remarks
 * Single column showing doctor information:
 * - Name/Display name
 * - Specialty badge
 * - Event count for the day
 */
export const APPOINTMENT_COLUMNS: any[] = [
  {
    type: 'resourceInfo',
    text: 'Doctor',
    width: 280,
    minWidth: 280,
    showImage: false,
    showEventCount: true,
    showRole: false,
    
    // Custom renderer for doctor info
    renderer: ({ record }: { record: any }) => {
      const data = record.data as {
        name?: string;
        specialty?: string;
        eventColor?: string;
      };
      
      const specialtyBadge = data.specialty
        ? `<span class="ml-2 px-1.5 py-0.5 text-xs rounded bg-slate-700 text-slate-300">
            ${data.specialty}
          </span>`
        : '';
      
      return `
        <div class="flex items-center justify-between w-full">
          <div class="flex flex-col">
            <span class="font-medium text-slate-200">${data.name || 'Doctor'}</span>
            ${specialtyBadge}
          </div>
        </div>
      `;
    },
  },
];

/**
 * Alternative: Multiple columns configuration (if needed)
 * 
 * @example
 * ```ts
 * export const APPOINTMENT_COLUMNS_DETAILED: BryntumColumn[] = [
 *   {
 *     text: 'Doctor',
 *     field: 'name',
 *     width: 180,
 *   },
 *   {
 *     text: 'Especialidad',
 *     field: 'specialty',
 *     width: 140,
 *   },
 *   {
 *     text: 'Citas',
 *     field: 'eventCount',
 *     width: 60,
 *     align: 'center',
 *   },
 * ];
 * ```
 */
