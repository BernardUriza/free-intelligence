"use client";

/**
 * Completion Celebration Component
 *
 * Simplified celebration for the conversational onboarding flow.
 * Shows confetti, badge unlock, and CTA to dashboard.
 *
 * Card: FI-ONBOARD-REDESIGN-001
 */

import { useEffect, useState, memo } from "react";
import { useRouter } from "next/navigation";
import confetti from "canvas-confetti";
import { ArrowRight, PartyPopper, Medal, Bot, Shield, Database } from "lucide-react";
import { Button } from "@/components/ui/button";

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

interface CompletionCelebrationProps {
  userName?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export const CompletionCelebration = memo(function CompletionCelebration({
  userName,
}: CompletionCelebrationProps) {
  const router = useRouter();
  const [showBadge, setShowBadge] = useState(false);
  const [showMessage, setShowMessage] = useState(false);

  /**
   * Fire confetti on mount
   */
  useEffect(() => {
    // Initial confetti burst
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#10b981", "#06b6d4", "#8b5cf6", "#f59e0b"],
    });

    // Delayed confetti bursts from sides
    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: ["#10b981", "#06b6d4"],
      });
    }, 300);

    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: ["#8b5cf6", "#f59e0b"],
      });
    }, 600);

    // Staggered reveal animations
    setTimeout(() => setShowBadge(true), 1000);
    setTimeout(() => setShowMessage(true), 1500);
  }, []);

  /**
   * Handle completion - redirect to dashboard
   */
  const handleFinish = () => {
    // Mark as completed
    localStorage.setItem("aurity_onboarding_completed", "true");
    localStorage.setItem("aurity_onboarding_completed_at", new Date().toISOString());

    // Redirect to dashboard
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full space-y-8">
        {/* Main Celebration */}
        <div className="text-center space-y-6">
          <div className="mb-6 animate-bounce flex justify-center">
            <PartyPopper className="w-20 h-20 text-yellow-400" strokeWidth={1.5} />
          </div>

          <h1 className="text-3xl md:text-4xl font-bold text-emerald-400 mb-4">
            {userName ? `¡Bienvenido, ${userName}!` : "¡Onboarding Completado!"}
          </h1>

          <p className="text-lg text-slate-300 max-w-lg mx-auto">
            Ya eres parte de Free-Intelligence. Tu IA médica local está lista para documentar tus consultas.
          </p>
        </div>

        {/* Badge Unlock */}
        {showBadge && (
          <div className="flex justify-center animate-fade-in-up">
            <div className="relative p-6 bg-gradient-to-br from-emerald-950/50 to-cyan-950/50 border-2 border-emerald-500/50 rounded-2xl shadow-2xl max-w-sm">
              {/* Glow effect */}
              <div className="absolute inset-0 bg-emerald-400/10 blur-xl rounded-2xl" />

              <div className="relative text-center space-y-3">
                <div className="flex justify-center">
                  <Medal className="w-12 h-12 text-yellow-400" strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-bold text-emerald-300">Badge Desbloqueado</h3>
                <div className="p-3 bg-slate-900/60 rounded-xl border border-emerald-700/30">
                  <p className="text-sm font-semibold text-slate-200">AURITY Pioneer</p>
                  <p className="text-xs text-slate-400 mt-1">Primer usuario de Free-Intelligence</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Key Features Reminder */}
        {showMessage && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in-up">
            <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
              <Database className="w-8 h-8 mx-auto mb-2 text-emerald-400" strokeWidth={1.5} />
              <p className="text-sm font-medium text-slate-200">100% Local</p>
              <p className="text-xs text-slate-500 mt-1">Tus datos nunca salen</p>
            </div>
            <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
              <Shield className="w-8 h-8 mx-auto mb-2 text-cyan-400" strokeWidth={1.5} />
              <p className="text-sm font-medium text-slate-200">Encriptado</p>
              <p className="text-xs text-slate-500 mt-1">AES-256 + HIPAA ready</p>
            </div>
            <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-center">
              <Bot className="w-8 h-8 mx-auto mb-2 text-purple-400" strokeWidth={1.5} />
              <p className="text-sm font-medium text-slate-200">Notas SOAP</p>
              <p className="text-xs text-slate-500 mt-1">Documentación automática</p>
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="text-center pt-6">
          <Button
            onClick={handleFinish}
            variant="primary"
            size="xl"
            icon={ArrowRight}
            className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 shadow-lg hover:shadow-emerald-500/30 hover:scale-105 transition-all duration-200 px-10"
          >
            Ir al Dashboard
          </Button>
          <p className="text-xs text-slate-500 mt-4">
            Free-Intelligence estará esperándote
          </p>
        </div>
      </div>
    </div>
  );
});

export default CompletionCelebration;
