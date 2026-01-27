/**
 * Dashboard Constants and Configuration
 *
 * Centralizes magic numbers, mock data, and configuration
 * to improve maintainability and testability.
 */

// =============================================================================
// TIME & DURATION CONSTANTS
// =============================================================================

/** Estimated minutes per patient for wait time calculation */
export const ESTIMATED_MINUTES_PER_PATIENT = 8;

/** Auto-refresh interval for appointments (ms) */
export const APPOINTMENTS_REFRESH_INTERVAL = 30000; // 30 seconds

/** Auto-refresh interval for queue data (ms) */
export const QUEUE_REFRESH_INTERVAL = 10000; // 10 seconds

/** QR code refresh interval (ms) */
export const QR_REFRESH_INTERVAL = 240000; // 4 minutes

/** Default content display duration (ms) */
export const DEFAULT_CONTENT_DURATION = 15000; // 15 seconds

/** Doctor message display duration (ms) */
export const DOCTOR_MESSAGE_DURATION = 20000; // 20 seconds

/** Content cache TTL (ms) */
export const CONTENT_CACHE_TTL = 30 * 60 * 1000; // 30 minutes

// =============================================================================
// UI CONSTANTS
// =============================================================================

/** Maximum characters for TV messages */
export const MAX_MESSAGE_LENGTH = 280;

/** Number of next patients to show in queue preview */
export const NEXT_PATIENTS_PREVIEW_COUNT = 3;

/** Maximum appointments visible before scrolling */
export const MAX_VISIBLE_APPOINTMENTS = 10;

// =============================================================================
// KEYBOARD SHORTCUTS
// =============================================================================

export const KEYBOARD_SHORTCUTS = {
  CALL_NEXT: { key: 'n', ctrlKey: true, description: 'Llamar siguiente turno' },
  OPEN_TV: { key: 't', ctrlKey: true, description: 'Abrir vista TV' },
  PREV_SLIDE: { key: 'ArrowLeft', description: 'Slide anterior' },
  NEXT_SLIDE: { key: 'ArrowRight', description: 'Slide siguiente' },
  TOGGLE_PLAY: { key: ' ', description: 'Pausar/Reanudar auto-play' },
  REFRESH: { key: 'r', ctrlKey: true, description: 'Actualizar datos' },
} as const;

// =============================================================================
// QUICK MESSAGES POOL
// =============================================================================

export const QUICK_MESSAGES = [
  { id: 'delay', iconKey: 'clock', text: 'Retraso de 15 minutos en consultas' },
  { id: 'silence', iconKey: 'users', text: 'Favor de mantener silencio en sala de espera' },
  { id: 'water', iconKey: 'droplet', text: 'Agua disponible en el dispensador' },
  { id: 'documents', iconKey: 'clipboardList', text: 'Traer estudios previos a consulta' },
  { id: 'wait', iconKey: 'bell', text: 'Esperar llamado por nombre' },
  { id: 'mask', iconKey: 'heartPulse', text: 'Uso de cubrebocas obligatorio' },
  { id: 'sanitizer', iconKey: 'droplet', text: 'Gel antibacterial disponible en la entrada' },
  { id: 'phone', iconKey: 'smartphone', text: 'Favor de silenciar teléfonos celulares' },
] as const;

// =============================================================================
// QUEUE STATUS CONFIGURATION
// =============================================================================

export type QueueStatus = 'waiting' | 'called' | 'in_progress' | 'completed' | 'no_show';

export const QUEUE_STATUS_CONFIG: Record<QueueStatus, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  waiting: {
    label: 'En espera',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
  },
  called: {
    label: 'Llamado',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    borderColor: 'border-emerald-500/30',
  },
  in_progress: {
    label: 'En consulta',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
  },
  completed: {
    label: 'Completado',
    color: 'text-slate-400',
    bgColor: 'bg-slate-500/20',
    borderColor: 'border-slate-500/30',
  },
  no_show: {
    label: 'No asistió',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
  },
};

// =============================================================================
// MOCK DATA FOR DEVELOPMENT
// =============================================================================

export interface QueuePatient {
  ticketNumber: string;
  status: QueueStatus;
  estimatedWait?: number;
  checkinTime?: string;
}

export const MOCK_QUEUE_PATIENTS: QueuePatient[] = [
  { ticketNumber: 'A-012', status: 'in_progress', checkinTime: '09:15' },
  { ticketNumber: 'A-013', status: 'waiting', estimatedWait: 8 },
  { ticketNumber: 'A-014', status: 'waiting', estimatedWait: 16 },
  { ticketNumber: 'A-015', status: 'waiting', estimatedWait: 24 },
  { ticketNumber: 'A-016', status: 'waiting', estimatedWait: 32 },
];

// =============================================================================
// AI CONTENT CATEGORIES
// =============================================================================

export const AI_CONTENT_CATEGORIES = [
  { id: 'nutrition', label: 'Nutrición', iconKey: 'salad', description: 'Tips de alimentación saludable' },
  { id: 'exercise', label: 'Ejercicio', iconKey: 'footprints', description: 'Consejos de actividad física' },
  { id: 'mental_health', label: 'Salud Mental', iconKey: 'brain', description: 'Bienestar emocional' },
  { id: 'prevention', label: 'Prevención', iconKey: 'shield', description: 'Cuidados preventivos' },
  { id: 'hydration', label: 'Hidratación', iconKey: 'droplet', description: 'Importancia del agua' },
  { id: 'sleep', label: 'Sueño', iconKey: 'moon', description: 'Calidad del descanso' },
] as const;

export const AI_TRIVIA_DIFFICULTIES = [
  { id: 'easy', label: 'Fácil', description: 'Preguntas básicas de salud general' },
  { id: 'medium', label: 'Intermedio', description: 'Preguntas más específicas' },
  { id: 'hard', label: 'Difícil', description: 'Trivia avanzada de salud' },
] as const;

// =============================================================================
// TV LAYOUT CONFIGURATION
// =============================================================================

export const TV_LAYOUT_CONFIG = {
  mainContent: {
    cols: 'col-span-1 lg:col-span-3 xl:col-span-4',
    minHeight: '60vh',
  },
  sidePanel: {
    cols: 'col-span-1 lg:col-span-1 xl:col-span-1',
    qrWeight: 3,
    tipsWeight: 1,
  },
  aspectRatio: 16 / 9,
} as const;
