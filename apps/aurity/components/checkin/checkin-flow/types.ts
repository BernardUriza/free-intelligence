/**
 * CheckinFlow Types
 */

import type {
  CheckinStep,
  CheckinSession,
  IdentifyPatientResponse,
  PendingAction,
  CompleteCheckinResponse,
} from '@aurity-standalone/types/checkin';

export interface CheckinFlowProps {
  clinicId: string;
  clinicName?: string;
  onComplete?: (response: CompleteCheckinResponse) => void;
  onCancel?: () => void;
}

export type IdentificationMethod = 'code' | 'curp' | 'name_dob';

export interface FlowState {
  step: CheckinStep;
  session: CheckinSession | null;
  identificationMethod: IdentificationMethod;
  patientData: IdentifyPatientResponse | null;
  pendingActions: PendingAction[];
  completedActions: string[];
  skippedActions: string[];
  error: string | null;
  isLoading: boolean;
}

export interface IdentificationFormState {
  checkinCode: string;
  curp: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
}
