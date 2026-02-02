/**
 * Onboarding Page
 *
 * Card: FI-ONBOARD-REDESIGN-001
 * Demo: http://localhost:9000/onboarding
 *
 * Uses ChatWidget with useOnboardingChat hook for:
 * - Reusable chat infrastructure (streaming, voice, etc.)
 * - Custom quick reply chips for personalization
 * - 4-phase flow: intro → personalization → demo → complete
 */

"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { useOnboardingChat, type OnboardingUserData } from "@/hooks/useOnboardingChat";
import { CompletionCelebration } from "@/components/onboarding/CompletionCelebration";
import { SystemStatus } from "@/components/ui/SystemStatus";
import type { ChatConfig } from "@/config/chat.config";

// Onboarding-specific chat configuration
const onboardingChatConfig: Partial<ChatConfig> = {
  title: "Onboarding",
  subtitle: "Bienvenida a Free-Intelligence",
  theme: {
    background: {
      header: "bg-gradient-to-r from-emerald-600 to-cyan-600",
      body: "bg-slate-950",
      input: "bg-slate-800",
    },
    border: {
      main: "border-slate-700",
      input: "border-slate-700",
      bubble: "border-slate-600/60",
    },
    text: {
      primary: "text-white",
      secondary: "text-slate-200",
      muted: "text-slate-400",
      accent: "text-emerald-300",
    },
    accent: {
      from: "from-emerald-600",
      to: "to-cyan-600",
    },
    shadow: "shadow-2xl",
    timestamp: {
      text: "text-slate-400/70",
      tooltip: "bg-slate-800/95 text-slate-200",
    },
  },
  behavior: {
    autoScroll: true,
    showTyping: true,
    groupMessages: false,
    groupThresholdMinutes: 2,
    showDayDividers: false,
    animateEntrance: true,
    maxMessages: 50,
    inputPlaceholder: "Escribe tu respuesta...",
    enableReactions: false,
    enableReadReceipts: false,
    enableThinking: false, // Fast responses for onboarding
    showThinking: false,
  },
  footer: "100% Local · Tus datos nunca salen de tu red",
  dimensions: {
    width: "100%",
    height: "100%",
    minHeight: "100vh",
    maxHeight: "100vh",
  },
};

export default function OnboardingPage() {
  const router = useRouter();

  // Callbacks for onboarding events
  const handleSkip = useCallback(() => {
    router.push("/");
  }, [router]);

  const handleComplete = useCallback(
    (userData: OnboardingUserData) => {
      console.log("[Onboarding] Complete with data:", userData);
      // Could send analytics here
    },
    []
  );

  // Initialize onboarding chat hook
  const onboardingHook = useOnboardingChat({
    onSkip: handleSkip,
    onComplete: handleComplete,
  });

  // If complete, show celebration
  if (onboardingHook.phase === "complete") {
    return <CompletionCelebration userName={onboardingHook.userData.userName} />;
  }

  return (
    <div className="relative h-screen bg-slate-950">
      {/* LLM Status Indicator - Brain icon in top left corner */}
      <div className="absolute top-4 left-4 z-50">
        <SystemStatus />
      </div>

      {/* Skip Button */}
      <button
        type="button"
        onClick={onboardingHook.skipOnboarding}
        className="
          absolute top-4 right-4 z-50
          px-3 py-1.5 text-xs font-medium
          text-slate-500 hover:text-slate-300
          bg-slate-800/50 hover:bg-slate-700/50
          border border-slate-700/50 hover:border-slate-600/50
          rounded-full transition-all duration-200
        "
      >
        Omitir
      </button>

      {/* Demo Complete Button (for demo phase) */}
      {onboardingHook.phase === "demo" && !onboardingHook.isTyping && (
        <div className="absolute bottom-24 left-0 right-0 z-50 flex justify-center">
          <button
            type="button"
            onClick={onboardingHook.completeOnboarding}
            className="
              px-8 py-3 text-base font-semibold
              bg-gradient-to-r from-emerald-600 to-cyan-600
              hover:from-emerald-500 hover:to-cyan-500
              text-white rounded-xl
              shadow-lg hover:shadow-emerald-500/30
              transform hover:scale-105
              transition-all duration-200
            "
          >
            Completar Onboarding
          </button>
        </div>
      )}

      {/* Chat Widget - Fullscreen, Embedded Mode */}
      <ChatWidget
        config={onboardingChatConfig}
        initialOpen={true}
        initialMode="fullscreen"
        embedded={true}
        chatHook={onboardingHook}
      />
    </div>
  );
}
