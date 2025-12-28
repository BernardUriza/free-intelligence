"use client";

/**
 * Onboarding Flow Hook
 *
 * Manages the state machine and context for the onboarding flow
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useFIConversation } from '@aurity-standalone/hooks/useFIConversation';
import { WelcomeStep, SurveyStep } from "../steps";
import type { Phase, OnboardingContext, StepDefinition, StepCallbacks, StepStatus } from "../types";

const STORAGE_KEY = "fi_onboarding_progress";

const stepDefinitions: StepDefinition[] = [
  {
    id: "welcome",
    component: WelcomeStep,
    title: "Bienvenido",
    description: "Conoce a Free-Intelligence",
  },
  {
    id: "survey",
    component: SurveyStep,
    canProceed: (context) => !!(
      context.survey.userRole &&
      context.survey.clinicType &&
      context.survey.consultasPerDay &&
      context.survey.aiExperience
    ),
    title: "Personalización",
    description: "Ayúdanos a conocer tu práctica médica",
  },
  // Add other steps later
];

const phaseOrder: Phase[] = ["welcome", "survey", "glitch", "beta", "residencia", "patient_setup", "consultation", "export", "complete"];

export function useOnboardingFlow() {
  const router = useRouter();
  const [currentPhase, setCurrentPhase] = useState<Phase>("welcome");
  const [context, setContext] = useState<OnboardingContext>({
    survey: {},
    patient: { nombre: '', edad: '', genero: '', motivoConsulta: '' },
  });
  // FI Conversation hook for Phase 0 (Welcome)
  const {
    messages,
    loading: fiLoading,
    isTyping,
  } = useFIConversation({
    phase: 'welcome',
    storageKey: 'fi_onboarding_conversation',
    autoIntroduction: currentPhase === 'welcome',
  });

  // Status for step components
  const status: StepStatus = useMemo(() => ({
    busy: fiLoading,
  }), [fiLoading]);

  // Update context with FI data
  useEffect(() => {
    setContext(prev => ({ ...prev, messages, isTyping }));
  }, [messages, isTyping]);

  // Load from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const state = JSON.parse(saved);
        setCurrentPhase(state.phase);
        setContext(prev => ({ ...prev, survey: state.survey || {} }));
      }
    } catch (error) {
      console.error("Failed to load onboarding progress:", error);
    }
  }, []);

  // Save to localStorage
  useEffect(() => {
    try {
      const state = { phase: currentPhase, survey: context.survey };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      console.error("Failed to save onboarding progress:", error);
    }
  }, [currentPhase, context.survey]);

  const updateContext = useCallback((updates: Partial<OnboardingContext>) => {
    setContext(prev => ({ ...prev, ...updates }));
  }, []);

  const next = useCallback(() => {
    const currentIndex = phaseOrder.indexOf(currentPhase);
    if (currentIndex < phaseOrder.length - 1) {
      setCurrentPhase(phaseOrder[currentIndex + 1]);
    }
  }, [currentPhase]);

  const back = useCallback(() => {
    const currentIndex = phaseOrder.indexOf(currentPhase);
    if (currentIndex > 0) {
      setCurrentPhase(phaseOrder[currentIndex - 1]);
    }
  }, [currentPhase]);

  const complete = useCallback(() => {
    localStorage.setItem('aurity_onboarding_completed', 'true');
    router.push('/');
  }, [router]);

  const skip = useCallback(() => {
    localStorage.setItem('aurity_onboarding_completed', 'true');
    localStorage.setItem('aurity_onboarding_skipped', 'true');
    router.push('/');
  }, [router]);

  const callbacks: StepCallbacks = {
    next,
    back,
    skip,
    complete,
    updateContext,
  };

  const currentStepDef = stepDefinitions.find(s => s.id === currentPhase);

  return {
    currentPhase,
    context,
    status,
    callbacks,
    currentStepDef,
  };
}