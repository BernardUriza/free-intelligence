/**
 * Speaker label constants and utilities
 *
 * Centralizes speaker identification logic to avoid magic strings
 * scattered across components.
 */

export const SPEAKER_LABELS = {
  DOCTOR: ['MEDICO', 'Doctor', 'doctor', 'médico'],
  PATIENT: ['PACIENTE', 'Paciente', 'paciente'],
} as const;

/**
 * Check if speaker label represents a doctor
 */
export function isDoctor(speaker: string): boolean {
  return SPEAKER_LABELS.DOCTOR.includes(speaker as any);
}

/**
 * Check if speaker label represents a patient
 */
export function isPatient(speaker: string): boolean {
  return SPEAKER_LABELS.PATIENT.includes(speaker as any);
}

/**
 * Normalize speaker label for display
 */
export function normalizeSpeakerLabel(speaker: string): 'Doctor' | 'Paciente' | string {
  if (isDoctor(speaker)) return 'Doctor';
  if (isPatient(speaker)) return 'Paciente';
  return speaker;
}
