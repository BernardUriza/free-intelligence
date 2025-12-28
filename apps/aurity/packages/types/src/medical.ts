/**
 * Medical AI Workflow types
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-14
 */

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Masculino' | 'Femenino' | 'Otro';
  medicalHistory: string[];
  dateOfBirth?: string;
  allergies?: string[];
  currentMedications?: string[];
  bloodType?: string;
  chronicConditions?: string[];
}

export interface ClinicalNote {
  id: string;
  timestamp: string;
  note: string;
  category: 'subjective' | 'objective' | 'assessment' | 'plan';
  author?: string;
}

export interface Order {
  id: string;
  type: 'lab' | 'imaging' | 'prescription' | 'referral' | 'procedure';
  description: string;
  status: 'pending' | 'completed' | 'cancelled';
  timestamp: string;
  priority?: 'routine' | 'urgent' | 'stat';
}

export interface Encounter {
  id: string;
  patientId: string;
  sessionId?: string;
  startTime: string;
  endTime?: string;
  duration: number;
  chiefComplaint?: string;
  clinicalNotes: ClinicalNote[];
  orders: Order[];
  status: 'active' | 'paused' | 'completed';
}

export type WorkflowStep = 'escuchar' | 'revisar' | 'notas' | 'evidencia' | 'ordenes' | 'resumen';

export interface WorkflowState {
  currentStep: WorkflowStep;
  completedSteps: Set<string>;
  encounterData: Partial<Encounter>;
  isDirty: boolean; // Has unsaved changes
  lastSaved?: string;
}

export interface MedicalWorkflowProps {
  onNext?: () => void;
  onPrevious?: () => void;
  onSave?: (data: Partial<Encounter>) => Promise<void>;
  isRecording?: boolean;
  setIsRecording?: (recording: boolean) => void;
  encounterData?: Partial<Encounter>;
  patient?: Patient;
}
