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
    <div className="celeb-wrapper">
      <div className="celeb-container">
        {/* Main Celebration */}
        <div className="celeb-hero">
          <div className="celeb-party-icon">
            <PartyPopper className="celeb-party-icon-svg" strokeWidth={1.5} />
          </div>

          <h1 className="celeb-title">
            {userName ? `¡Bienvenido, ${userName}!` : "¡Onboarding Completado!"}
          </h1>

          <p className="celeb-subtitle">
            Ya eres parte de Free-Intelligence. Tu IA médica local está lista para documentar tus consultas.
          </p>
        </div>

        {/* Badge Unlock */}
        {showBadge && (
          <div className="celeb-badge-row">
            <div className="celeb-badge-card">
              {/* Glow effect */}
              <div className="celeb-badge-glow" />

              <div className="celeb-badge-body">
                <div className="flex justify-center">
                  <Medal className="celeb-badge-icon" strokeWidth={1.5} />
                </div>
                <h3 className="celeb-badge-title">Badge Desbloqueado</h3>
                <div className="celeb-badge-label">
                  <p className="celeb-badge-name">AURITY Pioneer</p>
                  <p className="celeb-badge-desc">Primer usuario de Free-Intelligence</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Key Features Reminder */}
        {showMessage && (
          <div className="celeb-features-grid">
            <div className="celeb-feature-card">
              <Database className="celeb-feature-icon text-emerald-400" strokeWidth={1.5} />
              <p className="celeb-feature-title">100% Local</p>
              <p className="celeb-feature-desc">Tus datos nunca salen</p>
            </div>
            <div className="celeb-feature-card">
              <Shield className="celeb-feature-icon text-cyan-400" strokeWidth={1.5} />
              <p className="celeb-feature-title">Encriptado</p>
              <p className="celeb-feature-desc">AES-256 + HIPAA ready</p>
            </div>
            <div className="celeb-feature-card">
              <Bot className="celeb-feature-icon text-purple-400" strokeWidth={1.5} />
              <p className="celeb-feature-title">Notas SOAP</p>
              <p className="celeb-feature-desc">Documentación automática</p>
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
            className="celeb-cta-btn"
          >
            Ir al Dashboard
          </Button>
          <p className="celeb-footer-hint">
            Free-Intelligence estará esperándote
          </p>
        </div>
      </div>
    </div>
  );
});

export default CompletionCelebration;
