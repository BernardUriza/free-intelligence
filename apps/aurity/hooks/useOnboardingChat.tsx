/**
 * useOnboardingChat Hook
 *
 * Chat hook for the conversational onboarding flow.
 * Implements ChatHook interface to be injectable into ChatWidget.
 *
 * Features:
 * - 4 phases: intro → personalization → demo → complete
 * - DYNAMIC pills from LLM JSON responses
 * - Custom empty state for loading
 * - Calls introduction endpoint on mount
 *
 * Card: FI-ONBOARD-REDESIGN-001
 * Updated: 2026-02-03 - Dynamic pills from LLM JSON
 */

"use client";

import { useState, useEffect, useCallback, useRef, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  Sparkles,
  Stethoscope,
  Building2,
  Users,
  Clock,
  HeartPulse,
  Hospital,
  BriefcaseMedical,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import { useChat } from "./useChat";
import type { FIMessage, UserRole, ClinicType, BehaviorMetrics } from "@aurity-standalone/types/assistant";
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

// JSON response from LLM
interface LLMPill {
  value: string;
  label: string;
  icon?: string;
  description?: string;
}

interface LLMQuestion {
  header: string;
  field: string;
  pills: LLMPill[];
}

interface LLMResponse {
  message: string;
  question?: LLMQuestion;
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

// Icon mapping: string name → Lucide component
const ICON_MAP: Record<string, LucideIcon> = {
  stethoscope: Stethoscope,
  "heart-pulse": HeartPulse,
  users: Users,
  building: Building2,
  clock: Clock,
  "briefcase-medical": BriefcaseMedical,
  hospital: Hospital,
  "user-check": UserCheck,
};

// Fallback questions (used if JSON parsing fails)
const FALLBACK_QUESTIONS: Record<
  Exclude<keyof OnboardingUserData, "userName">,
  { prompt: string; options: QuickReplyOption[] }
> = {
  userRole: {
    prompt: "¿Cuál es tu rol principal?",
    options: [
      { value: "medico_general", label: "Médico General", icon: Stethoscope, description: "Atención primaria" },
      { value: "especialista", label: "Especialista", icon: HeartPulse, description: "Especialidad médica" },
      { value: "enfermera", label: "Enfermera/o", icon: Users, description: "Apoyo clínico" },
      { value: "administrador", label: "Administrativo", icon: Building2, description: "Gestión de clínica" },
    ],
  },
  clinicType: {
    prompt: "¿Qué tipo de clínica?",
    options: [
      { value: "privada", label: "Privada", icon: Building2, description: "Consultorio privado" },
      { value: "publica", label: "Pública", icon: Hospital, description: "Sector público" },
      { value: "mixta", label: "Mixta", icon: BriefcaseMedical, description: "Ambos sectores" },
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
// UTILITIES
// =============================================================================

/**
 * Try to parse JSON from a string, handling markdown code blocks
 */
function tryParseJSON(content: string): LLMResponse | null {
  try {
    // Remove markdown code blocks if present
    let cleaned = content.trim();
    if (cleaned.startsWith("```json")) {
      cleaned = cleaned.slice(7);
    } else if (cleaned.startsWith("```")) {
      cleaned = cleaned.slice(3);
    }
    if (cleaned.endsWith("```")) {
      cleaned = cleaned.slice(0, -3);
    }
    cleaned = cleaned.trim();

    // Try to parse
    const parsed = JSON.parse(cleaned);

    // Validate structure
    if (typeof parsed.message === "string") {
      return parsed as LLMResponse;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Convert LLM pills to QuickReplyOptions with icon components
 */
function convertPillsToOptions(pills: LLMPill[]): QuickReplyOption[] {
  return pills.map((pill) => ({
    value: pill.value,
    label: pill.label,
    icon: pill.icon ? ICON_MAP[pill.icon] : undefined,
    description: pill.description,
  }));
}

/**
 * Extract display message from content (handles both JSON and plain text)
 */
function extractDisplayMessage(content: string): string {
  const parsed = tryParseJSON(content);
  if (parsed) {
    return parsed.message;
  }
  return content;
}

// =============================================================================
// CUSTOM UI COMPONENTS
// =============================================================================

function OnboardingEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-12 px-4">
      <div className="relative mb-6">
        <div className="onboard-chat-avatar">
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
  const lastParsedMessageId = useRef<string | null>(null);

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

  // Parse JSON from new assistant messages and extract pills
  useEffect(() => {
    if (chatHook.isTyping || chatHook.loading) return;
    if (chatHook.messages.length === 0) return;

    // Find the last assistant message
    const lastMessage = chatHook.messages[chatHook.messages.length - 1];
    if (!lastMessage || lastMessage.role !== "assistant") return;

    // Skip if we already parsed this message
    const messageId = lastMessage.id ?? null;
    if (lastParsedMessageId.current === messageId) return;
    lastParsedMessageId.current = messageId;

    // Try to parse JSON
    const parsed = tryParseJSON(lastMessage.content);

    if (parsed?.question) {
      // LLM provided pills - use them!
      const field = parsed.question.field as keyof OnboardingUserData;
      const options = convertPillsToOptions(parsed.question.pills);

      setCurrentQuestion({
        field,
        prompt: parsed.question.header,
        options,
      });

      // Move to personalization phase if we were in intro
      if (phase === "intro" && userData.userName) {
        setPhase("personalization");
      }
    } else if (parsed && !parsed.question) {
      // Check if we're done with all questions
      if (
        phase === "personalization" &&
        userData.userRole &&
        userData.clinicType &&
        userData.consultasPerDay
      ) {
        // All data collected - move to complete
        setPhase("demo");
        setCurrentQuestion(null);
      } else if (phase === "intro" && !userData.userName) {
        // Intro phase - waiting for name
        setCurrentQuestion({
          field: "userName",
          prompt: "¿Cómo te llamas?",
        });
      }
    } else {
      // Failed to parse JSON - use fallback questions
      console.warn("[useOnboardingChat] Failed to parse JSON, using fallback");

      // Show personalization questions if:
      // 1. Already in personalization phase, OR
      // 2. Still in intro but name is already collected (race condition fix)
      const shouldShowPersonalizationQuestions =
        phase === "personalization" || (phase === "intro" && userData.userName);

      if (shouldShowPersonalizationQuestions) {
        // Determine which question to show based on collected data
        if (!userData.userRole) {
          setCurrentQuestion({
            field: "userRole",
            ...FALLBACK_QUESTIONS.userRole,
          });
        } else if (!userData.clinicType) {
          setCurrentQuestion({
            field: "clinicType",
            ...FALLBACK_QUESTIONS.clinicType,
          });
        } else if (!userData.consultasPerDay) {
          setCurrentQuestion({
            field: "consultasPerDay",
            ...FALLBACK_QUESTIONS.consultasPerDay,
          });
        } else {
          setPhase("demo");
          setCurrentQuestion(null);
        }
      } else if (phase === "intro" && !userData.userName) {
        setCurrentQuestion({
          field: "userName",
          prompt: "¿Cómo te llamas?",
        });
      }
    }
  }, [chatHook.messages, chatHook.isTyping, chatHook.loading, phase, userData]);

  // Fallback: Set question when entering personalization phase without pills
  // This handles the race condition when phase changes after message parsing
  useEffect(() => {
    // Only run when in personalization, not typing, and no current question
    if (phase !== "personalization") return;
    if (chatHook.isTyping || chatHook.loading) return;
    if (currentQuestion !== null) return;

    // Determine which question to show based on collected data
    if (!userData.userRole) {
      setCurrentQuestion({
        field: "userRole",
        ...FALLBACK_QUESTIONS.userRole,
      });
    } else if (!userData.clinicType) {
      setCurrentQuestion({
        field: "clinicType",
        ...FALLBACK_QUESTIONS.clinicType,
      });
    } else if (!userData.consultasPerDay) {
      setCurrentQuestion({
        field: "consultasPerDay",
        ...FALLBACK_QUESTIONS.consultasPerDay,
      });
    } else {
      // All done
      setPhase("demo");
    }
  }, [phase, currentQuestion, userData, chatHook.isTyping, chatHook.loading]);

  // Transform messages to extract display content from JSON
  const transformedMessages = useMemo(() => {
    return chatHook.messages.map((msg) => {
      if (msg.role === "assistant") {
        return {
          ...msg,
          content: extractDisplayMessage(msg.content),
        };
      }
      return msg;
    });
  }, [chatHook.messages]);

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

  // Wrapped sendMessageStream that handles intro phase transition
  const sendMessageStream = useCallback(
    async (message: string, metadata?: object) => {
      if (!message.trim()) return;

      // If in intro phase, extract name and transition BEFORE streaming
      if (phase === "intro" && currentQuestion?.field === "userName") {
        const name = message.trim().replace(/^(soy|me llamo|mi nombre es)\s*/i, "");
        setUserData((prev) => ({ ...prev, userName: name }));

        // Clear question before sending
        setCurrentQuestion(null);

        // Send via streaming (onboarding never sends BehaviorMetrics)
        await chatHook.sendMessageStream(message, metadata as BehaviorMetrics | undefined);

        // Move to personalization after sending
        setPhase("personalization");
        return;
      }

      // Default: just stream
      await chatHook.sendMessageStream(message, metadata as BehaviorMetrics | undefined);
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

      // Clear current question FIRST to avoid race condition
      setCurrentQuestion(null);

      // Update user data
      setUserData((prev) => ({ ...prev, [field]: value }));

      // Send as user message (use streaming to include conversation history)
      await chatHook.sendMessageStream(label);
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
    lastParsedMessageId.current = null;
    window.location.reload();
  }, []);

  // Custom empty state
  const customEmptyState = useMemo<ReactNode>(() => {
    if (chatHook.messages.length === 0) {
      return <OnboardingEmptyState />;
    }
    return undefined;
  }, [chatHook.messages.length]);

  // Custom quick replies - show when we have a question with options
  const customQuickReplies = useMemo<ReactNode>(() => {
    if (
      currentQuestion?.options &&
      currentQuestion.options.length > 0 &&
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
  }, [currentQuestion, chatHook.isTyping, chatHook.loading, selectChip]);

  // Return ChatHook-compatible interface + onboarding extras
  return {
    // ChatHook interface (required) - use transformed messages
    messages: transformedMessages,
    loading: chatHook.loading,
    isTyping: chatHook.isTyping,
    sendMessage,

    // ChatHook interface (optional)
    loadingInitial: chatHook.loadingInitial,
    hasMoreMessages: false,
    loadingOlder: false,
    streamingMessage: chatHook.streaming?.content,
    loadOlderMessages: undefined,
    clearConversation: chatHook.clearConversation,
    getIntroduction: async () => { await chatHook.getIntroduction(); },
    customEmptyState,
    customQuickReplies,
    sendMessageStream,
    streaming: chatHook.streaming,

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
