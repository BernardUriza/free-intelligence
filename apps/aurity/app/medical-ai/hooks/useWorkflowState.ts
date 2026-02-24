/**
 * useWorkflowState Hook
 *
 * Single Responsibility: step navigation, recording state,
 * and completed-step tracking for the medical workflow.
 */

import { useState, useCallback } from 'react';
import { WorkflowStep } from '@aurity-standalone/types/medical';
import { MedicalWorkflowSteps } from '../WorkflowSteps';

export function useWorkflowState() {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('escuchar');
  const [isRecording, setIsRecording] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());

  const currentStepIndex = MedicalWorkflowSteps.findIndex((s) => s.id === currentStep);
  const progress = ((currentStepIndex + 1) / MedicalWorkflowSteps.length) * 100;

  const goToNextStep = useCallback(() => {
    if (currentStepIndex < MedicalWorkflowSteps.length - 1) {
      setCompletedSteps((prev) => new Set([...Array.from(prev), currentStep]));
      setCurrentStep(MedicalWorkflowSteps[currentStepIndex + 1].id);
    }
  }, [currentStepIndex, currentStep]);

  const goToPreviousStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStep(MedicalWorkflowSteps[currentStepIndex - 1].id);
    }
  }, [currentStepIndex]);

  /** Reset workflow to initial state */
  const resetWorkflow = useCallback(() => {
    setCurrentStep('escuchar');
    setCompletedSteps(new Set());
  }, []);

  return {
    currentStep,
    setCurrentStep,
    currentStepIndex,
    isRecording,
    setIsRecording,
    completedSteps,
    progress,
    goToNextStep,
    goToPreviousStep,
    resetWorkflow,
  };
}
