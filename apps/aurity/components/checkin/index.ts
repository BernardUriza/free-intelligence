/**
 * Check-in Components
 *
 * Card: FI-CHECKIN-001
 * Export all check-in related components
 */

export { CheckinQRDisplay } from './CheckinQRDisplay';
export { CheckinFlow } from './checkin-flow';
export { ReceptionistChatWidget } from './ReceptionistChatWidget';

// Re-export types for convenience
export type {
  CheckinStep,
  CheckinSession,
  Appointment,
  AppointmentStatus,
  AppointmentType,
  PendingAction,
  PendingActionType,
  WaitingRoomState,
  WaitingRoomPatient,
} from '@aurity-standalone/types/checkin';

// Re-export API and helpers
export {
  checkinAPI,
  formatCheckinCode,
  isValidCurp,
  maskCurp,
  formatWaitTime,
  getActionIcon,
} from '@aurity-standalone/api-client/checkin';
