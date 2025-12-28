/**
 * ClinicalNotes Types
 */

import type { LucideIcon } from 'lucide-react';

export interface ClinicalNotesProps {
  sessionId: string;
  onNext?: () => void;
  onPrevious?: () => void;
  className?: string;
}

export interface VitalSigns {
  temperature: string;
  heartRate: string;
  bloodPressure: string;
  respiratoryRate: string;
  oxygenSaturation: string;
}

export interface Diagnosis {
  code: string;
  description: string;
  severity?: string;
}

export interface Medication {
  name: string;
  dose: string;
  frequency: string;
  duration?: string;
  route?: string;
}

export interface SOAPData {
  chiefComplaint: string;
  hpi: string;
  allergies: string[];
  currentMedications: string[];
  vitalSigns: VitalSigns;
  physicalExam: string;
  primaryDiagnosis: Diagnosis | null;
  differentialDiagnoses: Diagnosis[];
  medications: Medication[];
  diagnosticTests: string[];
  followUp: string;
}

export interface AISuggestion {
  type: 'warning' | 'suggestion' | 'insight';
  content: string;
  confidence: number;
  source: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export type SOAPGenerationStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'error'
  | null;

export interface SuggestionStyles {
  bg: string;
  border: string;
  text: string;
  icon: LucideIcon;
}
