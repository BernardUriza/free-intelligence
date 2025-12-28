"use client";

/**
 * Completion Celebration Component - Phase 8 (FI-ONBOARD-008)
 *
 * Gamified completion experience with:
 * - Confetti animation
 * - Badge unlock
 * - Progress heatmap
 * - FI final message
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import confetti from "canvas-confetti";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProgressHeatmap } from "./ProgressHeatmap";

interface CompletionCelebrationProps {
  userName?: string;
  completionTimeMinutes?: number;
  quizScore?: number;
}

export function CompletionCelebration({
  userName,
  completionTimeMinutes,
  quizScore,
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
      colors: ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b'],
    });

    // Delayed confetti bursts
    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: ['#10b981', '#06b6d4'],
      });
    }, 300);

    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: ['#8b5cf6', '#f59e0b'],
      });
    }, 600);

    // Show badge after animation
    setTimeout(() => setShowBadge(true), 1000);
    setTimeout(() => setShowMessage(true), 1500);
  }, []);

  /**
   * Determine achievement tier
   */
  const getAchievementTier = (): { tier: string; icon: string; color: string } => {
    if (completionTimeMinutes && completionTimeMinutes < 15) {
      return { tier: 'Speed Runner', icon: '⚡', color: 'text-yellow-400' };
    } else if (quizScore && quizScore >= 90) {
      return { tier: 'Philosophy Master', icon: '🧠', color: 'fi-text-purple' };
    } else {
      return { tier: 'Thorough Explorer', icon: '🔍', color: 'fi-text-info' };
    }
  };

  const achievement = getAchievementTier();

  /**
   * Handle completion
   */
  const handleFinish = () => {
    // Mark as completed
    localStorage.setItem('aurity_onboarding_completed', 'true');
    localStorage.setItem('aurity_onboarding_completed_at', new Date().toISOString());

    // Redirect to dashboard
    router.push('/');
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Main Celebration */}
      <div className="text-center space-y-6">
        <div className="text-8xl mb-6 animate-bounce">🎉</div>

        <h1 className="text-4xl md:text-5xl font-bold fi-text-success mb-4">
          ¡Onboarding Completado!
        </h1>

        <p className="text-xl fi-text max-w-2xl mx-auto">
          {userName ? `¡Felicidades, ${userName}! ` : ''}
          Has completado el recorrido por AURITY. Ahora eres parte del sistema.
        </p>
      </div>

      {/* Badge Unlock */}
      {showBadge && (
        <div className="flex justify-center animate-fade-in-up">
          <div className="relative p-8 bg-gradient-to-br from-emerald-950/50 to-cyan-950/50 border-2 border-emerald-500/50 rounded-2xl shadow-2xl max-w-md">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-emerald-400/10 blur-xl rounded-2xl" />

            <div className="relative text-center space-y-4">
              <div className="text-6xl mb-4">🏅</div>
              <h3 className="text-2xl font-bold text-emerald-300">Badge Unlocked!</h3>
              <div className="p-4 bg-slate-900/60 rounded-xl border border-emerald-700/30">
                <p className="fi-section-title">
                  AURITY Pioneer
                </p>
                <p className="fi-subtitle">
                  Completed full onboarding flow · First user badge
                </p>
              </div>

              {/* Achievement Tier */}
              <div className="pt-4 fi-border-top/50">
                <p className="fi-text-xs-muted mb-2">Special Achievement:</p>
                <div className="flex items-center justify-center gap-2">
                  <span className="text-3xl">{achievement.icon}</span>
                  <span className={`text-lg font-semibold ${achievement.color}`}>
                    {achievement.tier}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Progress Heatmap */}
      <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-700/50">
        <h3 className="text-lg font-semibold text-slate-200 mb-4 text-center">
          📊 Your Onboarding Journey
        </h3>
        <ProgressHeatmap
          phases={[
            { name: 'Welcome', completed: true, date: new Date() },
            { name: 'Survey', completed: true, date: new Date() },
            { name: 'Glitch', completed: true, date: new Date() },
            { name: 'Beta', completed: true, date: new Date() },
            { name: 'Residencia', completed: true, date: new Date() },
            { name: 'Patient Setup', completed: true, date: new Date() },
            { name: 'Consultation', completed: true, date: new Date() },
            { name: 'Export', completed: true, date: new Date() },
          ]}
        />
      </div>

      {/* FI Final Message */}
      {showMessage && (
        <div className="p-6 bg-slate-900/60 backdrop-blur-xl rounded-xl border border-purple-700/30 animate-fade-in-up">
          <div className="flex items-start gap-4">
            <span className="text-4xl">🤖</span>
            <div>
              <p className="text-sm font-semibold text-purple-300 mb-3">
                Free-Intelligence · Tone: Empathetic + Sharp (Despedida)
              </p>
              <div className="space-y-3 fi-text leading-relaxed">
                <p>
                  Has completado el onboarding. Ahora eres parte del sistema.
                </p>
                <p>
                  Recuerda:
                </p>
                <ul className="list-none space-y-2 pl-4">
                  <li className="flex items-start gap-2">
                    <span className="fi-text-error mt-1">▸</span>
                    <span><strong className="fi-text-error">Materia = Glitch</strong> · Error budgets son contratos, no fallas</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="fi-text-purple mt-1">▸</span>
                    <span><strong className="fi-text-purple">Humano = Beta</strong> · Iteración perpetua, micro-coaching obsesivo</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="fi-text-success mt-1">▸</span>
                    <span><strong className="fi-text-success">Residencia = Soberanía</strong> · Tus datos, tu infraestructura, tu control</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="fi-text-info mt-1">▸</span>
                    <span><strong className="fi-text-info">Gnóstico = Tester</strong> · Validación constante, evidencia siempre</span>
                  </li>
                </ul>
                <p className="pt-4 fi-border-top/50 text-slate-400 italic">
                  Nos vemos en las consultas. —FI
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-cyan-950/20 border border-cyan-700/30 rounded-xl text-center">
          <p className="text-3xl font-bold fi-text-info">8/8</p>
          <p className="fi-text-xs mt-1">Phases Completed</p>
        </div>
        <div className="p-4 bg-purple-950/20 border border-purple-700/30 rounded-xl text-center">
          <p className="text-3xl font-bold fi-text-purple">
            {completionTimeMinutes ? `${completionTimeMinutes}m` : 'N/A'}
          </p>
          <p className="fi-text-xs mt-1">Time Invested</p>
        </div>
        <div className="p-4 bg-emerald-950/20 border border-emerald-700/30 rounded-xl text-center">
          <p className="text-3xl font-bold fi-text-success">100%</p>
          <p className="fi-text-xs mt-1">Completion Rate</p>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center pt-8">
        <Button
          onClick={handleFinish}
          variant="primary"
          size="xl"
          icon={ArrowRight}
          className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 shadow-2xl hover:shadow-emerald-500/50 hover:scale-105 px-12"
        >
          Ir al Dashboard
        </Button>
        <p className="fi-text-xs-muted mt-4">
          Free-Intelligence estará esperándote
        </p>
      </div>
    </div>
  );
}
