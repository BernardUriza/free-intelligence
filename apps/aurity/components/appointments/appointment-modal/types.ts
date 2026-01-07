/**
 * AppointmentModal Types
 */

export type AppointmentId = string;

export interface AppointmentDraft {
  patient_id: string;
  doctor_id: string;
  scheduled_date: string; // YYYY-MM-DD
  scheduled_time: string; // HH:mm
  appointment_type: 'FIRST_TIME' | 'FOLLOW_UP' | 'PROCEDURE' | 'EMERGENCY' | 'TELEMEDICINE';
  estimated_duration: number; // minutes
  reason: string;
  notes?: string;
}

export interface AppointmentModalProps {
  mode: 'create' | 'edit';
  isOpen: boolean;
  onClose: () => void;
  onCancel: () => void;
  onSubmit: (payload: {
    appointment_id?: AppointmentId;
    patient_id: string;
    doctor_id: string;
    scheduled_at: string; // ISO
    appointment_type: AppointmentDraft['appointment_type'];
    estimated_duration: number;
    reason: string;
    notes?: string;
  }) => Promise<void>;
  onDelete?: (id: AppointmentId) => Promise<void>;
  doctors: Doctor[];
  initialData?: Partial<AppointmentDraft & { appointment_id: AppointmentId }>;
  prefilledData?: { date?: Date; doctorId?: string; endDate?: Date } | null;
  // Customization props for unified modal
  submitButtonText?: string;    // Override submit button text (default: "Crear Cita" / "Guardar Cambios")
  hideDoctorField?: boolean;    // Hide doctor selector when doctor is implicit (e.g., MedicalAI)
  onAfterSubmit?: () => void;   // Callback after successful submit (e.g., start workflow)
}

// Re-export Doctor type from bryntum utils
import type { Doctor } from '@/components/bryntum/utils/appointment-transform.utils';
export type { Doctor };

export interface NewPatientForm {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  email: string;
  phone: string;
}
