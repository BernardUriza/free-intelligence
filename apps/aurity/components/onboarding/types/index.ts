/**
 * Onboarding Domain Types
 *
 * Defines contracts for the onboarding flow orchestration
 */

import type { FIMessage, UserRole, ClinicType, AIExperience } from '@aurity-standalone/types/assistant';

export type Phase = "welcome" | "survey" | "glitch" | "beta" | "residencia" | "patient_setup" | "consultation" | "export" | "complete";

export type ConsultasPerDay = '1-5' | '6-15' | '16-30' | '31+';

export interface SurveyData {
  userRole?: UserRole;
  clinicType?: ClinicType;
  consultasPerDay?: ConsultasPerDay;
  aiExperience?: AIExperience;
}

export interface PatientFormData {
  nombre: string;
  edad: string;
  genero: string;
  motivoConsulta: string;
}

export interface OnboardingContext {
  survey: SurveyData;
  patient: PatientFormData;
  quizAnswer?: string | null;
  showFeedback?: boolean;
  messages?: FIMessage[];
  isTyping?: boolean;
}

export interface StepCallbacks {
  next: () => void;
  back?: () => void;
  skip?: () => void;
  complete: () => void;
  updateContext: (updates: Partial<OnboardingContext>) => void;
}

export interface StepStatus {
  busy: boolean;
  error?: string;
}

export interface StepProps {
  context: OnboardingContext;
  callbacks: StepCallbacks;
  status: StepStatus;
}

export interface StepDefinition {
  id: Phase;
  component: React.ComponentType<StepProps>;
  canProceed?: (context: OnboardingContext) => boolean;
  title: string;
  description?: string;
}

// Re-export types from external modules for convenience
export type { UserRole, ClinicType, AIExperience, FIMessage };