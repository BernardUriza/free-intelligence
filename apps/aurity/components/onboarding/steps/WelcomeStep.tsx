"use client";

/**
 * Welcome Step - Meet Free-Intelligence
 */

import { Button } from "@/components/ui/button";
import { OnboardingMessage } from "@/components/ui/message";
import { FITypingIndicator } from "../FITypingIndicator";
import type { StepProps } from "../types";

export function WelcomeStep({ context, callbacks, status }: StepProps) {
  const messages = context.messages || [];
  const isTyping = context.isTyping || false;

  return (
    <div className="fi-stack-xl">
      {/* Page Title */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-slate-50 mb-2">
          Bienvenido a AURITY
        </h1>
        <p className="text-slate-400">
          Conoce a Free-Intelligence, tu asistente residente
        </p>
      </div>

      {/* FI Conversation */}
      <div className="space-y-4 max-w-3xl mx-auto">
        {/* Display FI introduction message */}
        {messages.map((msg, idx) => (
          <OnboardingMessage
            key={idx}
            message={msg}
            showTimestamp={false}
            animate
          />
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <FITypingIndicator
            show
            persona="onboarding_guide"
          />
        )}
      </div>

      {/* CTA: Proceed to survey */}
      {messages.length > 0 && !status.busy && (
        <div className="text-center mt-12">
          <Button onClick={callbacks.next} size="xl">
            Continuar con la personalización →
          </Button>
        </div>
      )}
    </div>
  );
}