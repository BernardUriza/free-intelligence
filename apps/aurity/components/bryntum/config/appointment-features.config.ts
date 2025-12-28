/**
 * Appointments Features Configuration
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Bryntum Scheduler features optimized for medical appointments.
 * Enables drag/drop, resize, editing with appointment-specific validations.
 */

import type { SchedulerFeatures } from '../types/scheduler.types';

/**
 * Appointment Status Colors
 * Maps appointment status to Bryntum event colors
 */
export const APPOINTMENT_STATUS_COLORS: Record<string, string> = {
  scheduled: 'blue',       // Initial scheduled state
  confirmed: 'green',      // Patient confirmed
  checked_in: 'teal',      // Patient arrived and checked in
  in_progress: 'orange',   // Doctor currently with patient
  completed: 'gray',       // Appointment finished
  cancelled: 'red',        // Cancelled by clinic/patient
  no_show: 'yellow',       // Patient didn't show up
};

/**
 * Doctor Specialty Colors
 * Visual color coding for different medical specialties
 */
export const SPECIALTY_COLORS: Record<string, string> = {
  'Medicina General': 'blue',
  'Pediatría': 'green',
  'Cardiología': 'red',
  'Dermatología': 'purple',
  'Ginecología': 'pink',
  'Traumatología': 'orange',
  'Neurología': 'indigo',
  'Oftalmología': 'cyan',
};

/**
 * Appointments Features Configuration
 * 
 * @remarks
 * Key differences from timeline features:
 * - eventDrag: Enabled with resource constraint (can't drag to different doctor)
 * - eventResize: Enabled (adjust appointment duration)
 * - eventEdit: Custom fields for patient, reason, type
 * - Tooltips show patient info and check-in codes
 */
export const APPOINTMENT_FEATURES: SchedulerFeatures = {
  // Drag & Drop
  eventDrag: {
    constrainDragToResource: true, // Appointments can't move between doctors
    showTooltip: true,
    showExactDropPosition: true,
  },
  
  // CRITICAL: Allow drawing blocks via drag (creates temporary event)
  eventDragCreate: {
    showTooltip: true,
    // Event will be validated and confirmed via custom modal
  },
  
  // Resize appointments to adjust duration
  eventResize: {
    showTooltip: true,
    // Note: validatorFn might not be available in all Bryntum versions
    // Validation handled in beforeEventEdit listener instead
  },
  
  // Event Editor disabled - using custom NewAppointmentModal instead
  eventEdit: false,
  
  // Tooltip with patient details
  eventTooltip: {
    template: ({ eventRecord }) => {
      const data = eventRecord.data as Record<string, unknown>;
      return `
        <div class="p-3 max-w-xs">
          <div class="font-bold text-base mb-2">
            ${data.name || 'Cita médica'}
          </div>
          
          <div class="space-y-1 text-sm">
            <div class="flex items-center gap-2">
              <span class="text-slate-500">Paciente:</span>
              <span class="text-slate-200">${data.patient_name || 'No especificado'}</span>
            </div>
            
            <div class="flex items-center gap-2">
              <span class="text-slate-500">Código check-in:</span>
              <span class="font-mono text-cyan-400">${data.checkin_code || 'N/A'}</span>
            </div>
            
            ${data.reason ? `
              <div class="mt-2 pt-2 border-t border-slate-700">
                <div class="text-slate-500 text-xs mb-1">Motivo:</div>
                <div class="text-slate-300 text-xs">${data.reason}</div>
              </div>
            ` : ''}
            
            <div class="flex items-center gap-2 mt-2">
              <span class="text-slate-500">Estado:</span>
              <span class="px-2 py-0.5 rounded text-xs bg-slate-700">
                ${getStatusLabel(data.status as string)}
              </span>
            </div>
          </div>
        </div>
      `;
    },
  },
  
  // Context menu for quick actions
  eventMenu: {
    items: {
      // Custom menu items
      confirmAppointment: {
        text: 'Confirmar cita',
        icon: 'b-fa b-fa-check',
        weight: 100,
        onItem: ({ eventRecord }: { eventRecord: any }) => {
          // TODO: Update appointment status via API
          eventRecord.status = 'confirmed';
        },
      },
      checkIn: {
        text: 'Registrar check-in',
        icon: 'b-fa b-fa-sign-in-alt',
        weight: 200,
        onItem: ({ eventRecord }: { eventRecord: any }) => {
          eventRecord.status = 'checked_in';
        },
      },
      separator: {
        type: 'separator',
        weight: 300,
      },
      // editEvent removed - using custom modal via click
      // editEvent: false,
      deleteEvent: {
        text: 'Cancelar cita',
        icon: 'b-fa b-fa-times',
      },
    },
  },
  
  // Enable time ranges (e.g., lunch breaks, non-working hours)
  timeRanges: {
    showCurrentTimeLine: true,
    showHeaderElements: true,
  },

  // Show non-working time as disabled/grayed out
  nonWorkingTime: {
    // Visually distinguish non-working hours (before/after work_start_time and work_end_time)
    enableResizeToNonWorking: false, // Prevent resizing into non-working time
    enableDragToNonWorking: false,   // Prevent dragging into non-working time
  },

  // Enable resource-specific time ranges (per-doctor schedules)
  resourceTimeRanges: true,
  
  // Dependencies disabled (appointments are independent)
  dependencies: false,
};

/**
 * Get human-readable status label
 */
function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    scheduled: 'Programada',
    confirmed: 'Confirmada',
    checked_in: 'Check-in',
    in_progress: 'En curso',
    completed: 'Completada',
    cancelled: 'Cancelada',
    no_show: 'No asistió',
  };
  return labels[status] || status;
}

/**
 * Validation function for appointment operations
 * 
 * @param eventRecord - Bryntum event record
 * @returns true if valid, error message string if invalid
 */
export function validateAppointmentEdit(eventRecord: {
  data: Record<string, unknown>;
}): boolean | string {
  const status = eventRecord.data.status as string;
  
  // Can't edit completed or cancelled appointments
  if (status === 'completed' || status === 'cancelled') {
    return 'No se pueden modificar citas completadas o canceladas';
  }
  
  return true;
}

/**
 * Get color for appointment status
 */
export function getAppointmentColor(status: string): string {
  return APPOINTMENT_STATUS_COLORS[status] || 'blue';
}

/**
 * Get color for doctor specialty
 */
export function getSpecialtyColor(specialty: string | null): string {
  if (!specialty) return 'blue';
  return SPECIALTY_COLORS[specialty] || 'blue';
}
