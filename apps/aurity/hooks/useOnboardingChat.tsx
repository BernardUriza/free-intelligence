/**
 * useOnboardingChat Hook
 *
 * Chat hook for the conversational onboarding flow.
 * Implements ChatHook interface to be injectable into ChatWidget.
 *
 * Features:
 * - 4 phases: intro → personalization → demo → complete
 * - Quick reply chips for personalization questions
 * - Custom empty state for loading
 * - Calls introduction endpoint on mount
 *
 * Card: FI-ONBOARD-REDESIGN-001
 */

"use client";

import { useState, useEffect, useCallback, useRef, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Bot, Sparkles, Stethoscope, Building2, Users, Clock } from "lucide-react";
import { useChat } from "./useChat";
import type { FIMessage, UserRole, ClinicType } from "@aurity-standalone/types/assistant";
import type { ChatHook } from "@aurity-standalone/types/chat";

// =============================================================================
// TYPES
// =============================================================================

export type OnboardingPhase = "intro" | "personalization" | "demo" | "complete";

// Use the types from the assistant package but also export local mappings
type LocalUserRole = "medico_general" | "especialista" | "enfermera" | "administrador";
type LocalClinicType = "privada" | "publica" | "mixta";
type ConsultasPerDay = "1-5" | "6-15" | "16-30" | "31+";

export interface OnboardingUserData {
  userName?: string;
  userRole?: LocalUserRole;
  clinicType?: LocalClinicType;
  consultasPerDay?: ConsultasPerDay;
}

export interface QuickReplyOption {
  value: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  description?: string;
}

export interface CurrentQuestion {
  field: keyof OnboardingUserData;
  prompt: string;
  options?: QuickReplyOption[];
}

export interface UseOnboardingChatOptions {
  /** Called when user skips onboarding */
  onSkip?: () => void;
  /** Called when onboarding is complete */
  onComplete?: (userData: OnboardingUserData) => void;
}

export interface UseOnboardingChatReturn extends ChatHook {
  // Onboarding-specific state
  phase: OnboardingPhase;
  userData: OnboardingUserData;
  currentQuestion: CurrentQuestion | null;

  // Onboarding-specific actions
  selectChip: (value: string) => Promise<void>;
  skipOnboarding: () => void;
  completeOnboarding: () => void;
  resetOnboarding: () => void;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const STORAGE_KEY = "fi_onboarding";
const COMPLETED_KEY = "aurity_onboarding_completed";

const PERSONALIZATION_QUESTIONS: Record<
  Exclude<keyof OnboardingUserData, "userName">,
  { prompt: string; options: QuickReplyOption[] }
> = {
  userRole: {
    prompt: "¿Cuál es tu rol principal?",
    options: [
      { value: "medico_general", label: "Médico General", icon: Stethoscope, description: "Atiendo pacientes" },
      { value: "especialista", label: "Especialista", icon: Stethoscope, description: "Especialidad médica" },
      { value: "enfermera", label: "Enfermera/o", icon: Users, description: "Apoyo clínico" },
      { value: "administrador", label: "Administrativo", icon: Building2, description: "Gestión de clínica" },
    ],
  },
  clinicType: {
    prompt: "¿Qué tipo de clínica?",
    options: [
      { value: "privada", label: "Privada", description: "Consultorio privado" },
      { value: "publica", label: "Pública", description: "Sector público" },
      { value: "mixta", label: "Mixta", description: "Ambos sectores" },
    ],
  },
  consultasPerDay: {
    prompt: "¿Cuántas consultas atiendes al día?",
    options: [
      { value: "1-5", label: "1-5", icon: Clock, description: "Pocas consultas" },
      { value: "6-15", label: "6-15", icon: Clock, description: "Volumen moderado" },
      { value: "16-30", label: "16-30", icon: Clock, description: "Alto volumen" },
      { value: "31+", label: "31+", icon: Clock, description: "Muy alto volumen" },
    ],
  },
};

// =============================================================================
// CUSTOM UI COMPONENTS
// =============================================================================

function OnboardingEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-12 px-4">
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center animate-pulse">
          <Bot className="w-10 h-10 text-emerald-400" />
        </div>
        <Sparkles className="absolute -top-1 -right-1 w-6 h-6 text-cyan-400 animate-bounce" />
      </div>
      <p className="text-slate-400 text-sm text-center">
        Conectando con Free-Intelligence...
      </p>
    </div>
  );
}

interface QuickRepliesProps {
  question: CurrentQuestion;
  onSelect: (value: string) => void;
  disabled?: boolean;
}

function QuickReplies({ question, onSelect, disabled }: QuickRepliesProps) {
  if (!question.options) return null;

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-400 text-center">{question.prompt}</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {question.options.map((option) => {
          const Icon = option.icon;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onSelect(option.value)}
              disabled={disabled}
              className="
                flex items-center gap-2 px-4 py-2.5
                bg-slate-800/60 hover:bg-slate-700/60
                border border-slate-600/50 hover:border-emerald-500/50
                rounded-xl text-sm text-slate-200
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                hover:shadow-lg hover:shadow-emerald-500/10
              "
            >
              {Icon && <Icon className="w-4 h-4 text-emerald-400" />}
              <span>{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// HOOK
// =============================================================================

export function useOnboardingChat(
  options: UseOnboardingChatOptions = {}
): UseOnboardingChatReturn {
  const { onSkip, onComplete } = options;
  const router = useRouter();

  // Onboarding state
  const [phase, setPhase] = useState<OnboardingPhase>("intro");
  const [userData, setUserData] = useState<OnboardingUserData>({});
  const [currentQuestion, setCurrentQuestion] = useState<CurrentQuestion | null>(null);

  // Refs
  const introFetchedRef = useRef(false);
  const phaseChangedRef = useRef(false);

  // Map phase to backend-compatible phase
  const getBackendPhase = useCallback(() => {
    switch (phase) {
      case "intro":
        return "welcome" as const;
      case "personalization":
        return "survey" as const;
      case "demo":
        return "first_consult" as const;
      case "complete":
        return "complete" as const;
      default:
        return "welcome" as const;
    }
  }, [phase]);

  // Use the main chat hook
  const chatHook = useChat({
    phase: getBackendPhase(),
    context: {
      persona: "onboarding_guide",
      userRole: userData.userRole as UserRole | undefined,
      clinicType: userData.clinicType as ClinicType | undefined,
      consultasPerDay: userData.consultasPerDay,
    },
    storageKey: `${STORAGE_KEY}_messages`,
    autoIntroduction: false,
    enableThinking: false, // Fast responses
  });

  // Load saved progress
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const data = JSON.parse(saved);
        if (data.phase) setPhase(data.phase);
        if (data.userData) setUserData(data.userData);
      }
    } catch (e) {
      console.error("[useOnboardingChat] Failed to load progress:", e);
    }
  }, []);

  // Save progress
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ phase, userData }));
    } catch (e) {
      console.error("[useOnboardingChat] Failed to save progress:", e);
    }
  }, [phase, userData]);

  // Fetch introduction on mount
  useEffect(() => {
    if (
      phase === "intro" &&
      !introFetchedRef.current &&
      chatHook.messages.length === 0 &&
      !chatHook.loading
    ) {
      introFetchedRef.current = true;
      chatHook.getIntroduction();
    }
  }, [phase, chatHook.messages.length, chatHook.loading, chatHook.getIntroduction]);

  // Set current question for intro phase (after intro message)
  useEffect(() => {
    if (
      phase === "intro" &&
      chatHook.messages.length > 0 &&
      !chatHook.isTyping &&
      !currentQuestion
    ) {
      setCurrentQuestion({
        field: "userName",
        prompt: "¿Cómo te llamas?",
      });
    }
  }, [phase, chatHook.messages.length, chatHook.isTyping, currentQuestion]);

  // Update current question for personalization phase
  useEffect(() => {
    if (phase === "personalization" && !phaseChangedRef.current) {
      phaseChangedRef.current = true;

      if (!userData.userRole) {
        setCurrentQuestion({
          field: "userRole",
          ...PERSONALIZATION_QUESTIONS.userRole,
        });
      } else if (!userData.clinicType) {
        setCurrentQuestion({
          field: "clinicType",
          ...PERSONALIZATION_QUESTIONS.clinicType,
        });
      } else if (!userData.consultasPerDay) {
        setCurrentQuestion({
          field: "consultasPerDay",
          ...PERSONALIZATION_QUESTIONS.consultasPerDay,
        });
      } else {
        // All done, move to demo
        setPhase("demo");
        setCurrentQuestion(null);
      }

      phaseChangedRef.current = false;
    }
  }, [phase, userData]);

  // Send message (handles intro name input) - adapts to ChatHook interface
  const sendMessage = useCallback(
    async (message: string, _metadata?: object): Promise<void> => {
      if (!message.trim()) return;

      // If in intro phase, extract name
      if (phase === "intro" && currentQuestion?.field === "userName") {
        const name = message.trim().replace(/^(soy|me llamo|mi nombre es)\s*/i, "");
        setUserData((prev) => ({ ...prev, userName: name }));

        // Send to FI (ignore return value for ChatHook compatibility)
        await chatHook.sendMessage(message);

        // Move to personalization
        setPhase("personalization");
        setCurrentQuestion(null);
        return;
      }

      // Default: send to FI
      await chatHook.sendMessage(message);
    },
    [phase, currentQuestion, chatHook]
  );

  // Select chip (for personalization)
  const selectChip = useCallback(
    async (value: string) => {
      if (!currentQuestion) return;

      const field = currentQuestion.field as keyof OnboardingUserData;

      // Find the label for user-friendly message
      const option = currentQuestion.options?.find((o) => o.value === value);
      const label = option?.label || value;

      // Update user data
      setUserData((prev) => ({ ...prev, [field]: value }));

      // Send as user message
      await chatHook.sendMessage(label);

      // Clear current question to trigger next
      setCurrentQuestion(null);
    },
    [currentQuestion, chatHook]
  );

  // Skip onboarding
  const skipOnboarding = useCallback(() => {
    localStorage.setItem(COMPLETED_KEY, "true");
    localStorage.setItem(`${COMPLETED_KEY}_skipped`, "true");
    onSkip?.();
    router.push("/");
  }, [router, onSkip]);

  // Complete onboarding
  const completeOnboarding = useCallback(() => {
    localStorage.setItem(COMPLETED_KEY, "true");
    localStorage.setItem(`${COMPLETED_KEY}_at`, new Date().toISOString());
    setPhase("complete");
    onComplete?.(userData);
  }, [userData, onComplete]);

  // Reset onboarding
  const resetOnboarding = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(`${STORAGE_KEY}_messages`);
    localStorage.removeItem(COMPLETED_KEY);
    localStorage.removeItem(`${COMPLETED_KEY}_skipped`);
    localStorage.removeItem(`${COMPLETED_KEY}_at`);
    setPhase("intro");
    setUserData({});
    setCurrentQuestion(null);
    introFetchedRef.current = false;
    window.location.reload();
  }, []);

  // Custom empty state
  // En onboarding, SIEMPRE mostrar nuestro empty state mientras no hay mensajes
  // Esto evita que caiga a ChatStartScreen ("Hola, Bernard")
  const customEmptyState = useMemo<ReactNode>(() => {
    if (chatHook.messages.length === 0) {
      return <OnboardingEmptyState />;
    }
    return undefined;
  }, [chatHook.messages.length]);

  // Custom quick replies
  const customQuickReplies = useMemo<ReactNode>(() => {
    if (
      phase === "personalization" &&
      currentQuestion?.options &&
      !chatHook.isTyping &&
      !chatHook.loading
    ) {
      return (
        <QuickReplies
          question={currentQuestion}
          onSelect={selectChip}
          disabled={chatHook.loading || chatHook.isTyping}
        />
      );
    }
    return undefined;
  }, [phase, currentQuestion, chatHook.isTyping, chatHook.loading, selectChip]);

  // Return ChatHook-compatible interface + onboarding extras
  return {
    // ChatHook interface (required)
    messages: chatHook.messages,
    loading: chatHook.loading,
    isTyping: chatHook.isTyping,
    sendMessage,

    // ChatHook interface (optional)
    loadingInitial: chatHook.loadingInitial,
    hasMoreMessages: chatHook.hasMoreMessages,
    loadingOlder: chatHook.loadingOlder,
    streamingMessage: chatHook.streaming?.content,
    loadOlderMessages: chatHook.loadOlderMessages,
    clearConversation: chatHook.clearConversation,
    getIntroduction: async () => { await chatHook.getIntroduction(); },
    customEmptyState,
    customQuickReplies,

    // Onboarding-specific
    phase,
    userData,
    currentQuestion,
    selectChip,
    skipOnboarding,
    completeOnboarding,
    resetOnboarding,
  };
}

export default useOnboardingChat;
