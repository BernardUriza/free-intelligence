/**
 * Check-in Types
 *
 * Card: FI-CHECKIN-001
 * Types for patient self-service check-in system
 */

// =============================================================================
// APPOINTMENT TYPES
// =============================================================================

export type AppointmentStatus =
  | 'scheduled'      // Cita programada, paciente no ha llegado
  | 'confirmed'      // Paciente confirmó asistencia (reminder)
  | 'checked_in'     // Paciente hizo check-in en clínica
  | 'in_progress'    // Paciente en consulta
  | 'completed'      // Consulta terminada
  | 'no_show'        // Paciente no se presentó
  | 'cancelled';     // Cita cancelada

export type AppointmentType =
  | 'first_visit'    // Primera consulta
  | 'follow_up'      // Seguimiento
  | 'procedure'      // Procedimiento
  | 'emergency'      // Urgencia
  | 'telemedicine';  // Consulta virtual

export interface Appointment {
  appointment_id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string;

  // Scheduling
  scheduled_at: string; // ISO datetime
  estimated_duration: number; // minutes
  appointment_type: AppointmentType;

  // Status tracking
  status: AppointmentStatus;
  checked_in_at?: string | null;
  called_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;

  // Check-in code (6 digits, expires same day)
  checkin_code: string;
  checkin_code_expires_at: string;

  // Context
  reason?: string; // Motivo de consulta
  notes?: string; // Notas internas

  // Pending actions for check-in
  pending_actions: PendingAction[];

  // Timestamps
  created_at: string;
  updated_at: string;
}

// =============================================================================
// PENDING ACTIONS (Check-in tasks)
// =============================================================================

export type PendingActionType =
  | 'update_contact'     // Actualizar teléfono/email
  | 'update_insurance'   // Actualizar datos de seguro
  | 'sign_consent'       // Firmar consentimiento
  | 'sign_privacy'       // Firmar aviso de privacidad
  | 'pay_copay'          // Pagar copago
  | 'pay_balance'        // Pagar saldo pendiente
  | 'upload_labs'        // Subir estudios de laboratorio
  | 'upload_imaging'     // Subir estudios de imagen
  | 'fill_questionnaire' // Llenar cuestionario pre-consulta
  | 'verify_identity';   // Verificar identidad (foto ID)

export type PendingActionStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'skipped';

export interface PendingAction {
  action_id: string;
  action_type: PendingActionType;
  status: PendingActionStatus;

  // Display
  title: string;
  description?: string;
  icon?: string;

  // Requirements
  is_required: boolean;
  is_blocking: boolean; // If true, must complete before check-in

  // For payments
  amount?: number;
  currency?: string;

  // For documents
  document_type?: string;
  document_url?: string;
  signed_at?: string;

  // For uploads
  uploaded_file_id?: string;

  // Timestamps
  completed_at?: string | null;
}

// =============================================================================
// CHECK-IN SESSION
// =============================================================================

export type CheckinStep =
  | 'scan_qr'           // Inicial - escanear QR
  | 'identify'          // Identificación del paciente
  | 'confirm_identity'  // Confirmar que es el paciente correcto
  | 'pending_actions'   // Completar acciones pendientes
  | 'success'           // Check-in exitoso
  | 'error';            // Error en el proceso

export interface CheckinSession {
  session_id: string;
  clinic_id: string;

  // Progress
  current_step: CheckinStep;
  started_at: string;
  completed_at?: string | null;

  // Identification
  identification_method?: 'code' | 'curp' | 'name_dob';

  // Linked appointment (once identified)
  appointment_id?: string | null;
  patient_id?: string | null;

  // Device info
  device_type: 'mobile' | 'kiosk' | 'tablet';
  user_agent?: string;

  // Timestamps
  expires_at: string; // Session expires after 15 minutes
}

// =============================================================================
// WAITING ROOM STATE
// =============================================================================

export interface WaitingRoomPatient {
  patient_id: string;
  patient_name: string;
  appointment_id: string;

  // Status
  checked_in_at: string;
  position_in_queue: number;
  estimated_wait_minutes: number;

  // Doctor info
  doctor_id: string;
  doctor_name: string;

  // For TV display (privacy-aware)
  display_name: string; // "María G." or ticket number
  is_next: boolean;
}

export interface WaitingRoomState {
  clinic_id: string;

  // Current queue
  patients_waiting: WaitingRoomPatient[];
  total_waiting: number;

  // Metrics
  avg_wait_time_minutes: number;
  patients_seen_today: number;

  // Next appointment
  next_available_slot?: string | null;

  // Last updated
  updated_at: string;
}

// =============================================================================
// QR CODE
// =============================================================================

export interface CheckinQRData {
  clinic_id: string;
  generated_at: number; // Unix timestamp
  expires_at: number; // Unix timestamp (valid for 5 minutes)
  nonce: string; // Prevent replay attacks
}

export interface GenerateQRResponse {
  qr_data: string; // Base64 encoded QR image
  qr_url: string; // URL encoded in QR
  expires_at: string;
}

// =============================================================================
// API REQUEST/RESPONSE TYPES
// =============================================================================

// Identify patient
export interface IdentifyByCodeRequest {
  clinic_id: string;
  checkin_code: string;
}

export interface IdentifyByCurpRequest {
  clinic_id: string;
  curp: string;
}

export interface IdentifyByNameRequest {
  clinic_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string; // YYYY-MM-DD
}

export interface IdentifyPatientResponse {
  success: boolean;
  patient?: {
    patient_id: string;
    full_name: string;
    masked_curp?: string; // "GARM****01HDFRRL09"
  };
  appointment?: {
    appointment_id: string;
    scheduled_at: string;
    doctor_name: string;
    appointment_type: AppointmentType;
  };
  pending_actions?: PendingAction[];
  error?: string;
}

// Complete check-in
export interface CompleteCheckinRequest {
  session_id: string;
  appointment_id: string;
  completed_actions: string[]; // action_ids
  skipped_actions: string[]; // action_ids (non-required only)
}

export interface CompleteCheckinResponse {
  success: boolean;
  checkin_time: string;
  position_in_queue: number;
  estimated_wait_minutes: number;
  message: string; // "Te llamaremos por tu nombre"
  error?: string;
}

// Get waiting room state
export interface GetWaitingRoomRequest {
  clinic_id: string;
}

export interface GetWaitingRoomResponse {
  state: WaitingRoomState;
}
