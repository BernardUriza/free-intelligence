/**
 * Medical AI Workflow - Shared Types
 *
 * Interfaces consumed across the medical-ai module.
 */

import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';

/** Appointment submission payload from the modal */
export interface AppointmentSubmitData {
  patient_id: string;
  doctor_id: string;
  scheduled_at: string;
  appointment_type: string;
  estimated_duration: number;
  reason: string;
  notes?: string;
}

/** Data pending workflow start after appointment creation */
export interface PendingWorkflowData {
  patient_id: string;
  appointment: Appointment;
}
