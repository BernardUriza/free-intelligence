"use client";

/**
 * Onboarding Reset Utility Page
 *
 * Development/testing utility to reset onboarding state
 * Access: /onboarding/reset
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { Button } from '@/components/ui/button';
import { toastError, showInfo } from '@/lib/swal';
import { Trash2, BarChart2, ArrowLeft, RefreshCw, AlertTriangle, CheckCircle, FolderOpen, Loader2 } from 'lucide-react';
import { isDesktop } from '@/lib/config/deployment';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('OnboardingReset');

export default function OnboardingResetPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'idle' | 'resetting' | 'done'>('idle');

  /**
   * Reset all onboarding data (localStorage + filesystem on desktop)
   */
  const handleReset = async () => {
    setStatus('resetting');

    try {
      // Remove all onboarding-related LocalStorage keys
      localStorage.removeItem('fi_onboarding_progress');
      localStorage.removeItem('fi_onboarding_conversation');
      localStorage.removeItem('aurity_onboarding_completed');
      localStorage.removeItem('fi_onboarding_survey');
      // Desktop wizard state (localStorage fallback)
      localStorage.removeItem('aurity_desktop_setup_complete');
      localStorage.removeItem('aurity_fi_monitor_installed');

      // On desktop, also reset the wizard state file
      if (isDesktop() && typeof window !== 'undefined' && '__TAURI__' in window) {
        try {
          const { invoke } = await import('@tauri-apps/api/core');
          await invoke('reset_wizard_state');
          log.info('Desktop wizard state reset');
        } catch (tauriErr) {
          log.warn('Could not reset Tauri wizard state', { error: String(tauriErr) });
        }
      }

      setStatus('done');

      // Auto-redirect to onboarding page after 2 seconds
      setTimeout(() => {
        router.push('/onboarding');
      }, 2000);
    } catch (error) {
      log.error('Failed to reset onboarding', { error: String(error) });
      toastError('Error al reiniciar onboarding');
      setStatus('idle');
    }
  };

  /**
   * Check current onboarding state
   */
  const checkState = () => {
    const progress = localStorage.getItem('fi_onboarding_progress');
    const conversation = localStorage.getItem('fi_onboarding_conversation');
    const completed = localStorage.getItem('aurity_onboarding_completed');
    const survey = localStorage.getItem('fi_onboarding_survey');

    log.info('Onboarding state', {
      progress: progress ? JSON.parse(progress) : null,
      conversation: conversation ? JSON.parse(conversation) : null,
      completed: completed || 'false',
      survey: survey ? JSON.parse(survey) : null,
    });

    showInfo('Estado mostrado en consola', 'Presiona F12 para ver los detalles');
  };

  return (
    <AppTemplate
      headerConfig={{
        title: 'Reiniciar Onboarding',
        subtitle: 'Utility para desarrolladores',
        icon: 'settings',
        iconColor: 'text-orange-400',
        showBackButton: true,
        backPath: '/onboarding',
      }}
      maxWidth="3xl"
      padding="0"
      showGeometricBg={true}
    >
      <div className="onboard-reset-wrapper">
        <div className="onboard-reset-card">
          {/* Header */}
          <div>
            <div className="mb-4">
              <RefreshCw className="w-16 h-16 text-blue-400 mx-auto" strokeWidth={1.5} aria-hidden="true" />
            </div>
            <h1 className="text-3xl font-bold text-slate-50 mb-2">
              Reiniciar Onboarding
            </h1>
            <p className="text-slate-400">
              Utility para desarrolladores - Reinicia el flujo de onboarding
            </p>
          </div>

          {/* Status Display */}
          {status === 'idle' && (
            <div className="fi-stack-xl">
              <div className="p-4 bg-yellow-950/30 border border-yellow-700/50 rounded-lg">
                <p className="text-yellow-200 text-sm flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
                  Esto eliminará todo el progreso de onboarding guardado en LocalStorage
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-4">
                <Button
                  onClick={handleReset}
                  variant="danger"
                  size="xl"
                  icon={Trash2}
                >
                  Reiniciar Onboarding
                </Button>

                <Button
                  onClick={checkState}
                  variant="secondary"
                  size="lg"
                  icon={BarChart2}
                >
                  Ver Estado Actual (Consola)
                </Button>

                <Button
                  onClick={() => router.push('/onboarding')}
                  variant="ghost"
                  size="lg"
                  icon={ArrowLeft}
                >
                  Volver al Onboarding
                </Button>
              </div>
            </div>
          )}

          {status === 'resetting' && (
            <div className="space-y-4">
              <Loader2 className="w-10 h-10 text-blue-400 mx-auto animate-spin" strokeWidth={1.5} aria-hidden="true" />
              <p className="fi-text font-medium">
                Limpiando datos de LocalStorage...
              </p>
            </div>
          )}

          {status === 'done' && (
            <div className="space-y-4 animate-fade-in-up">
              <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto" strokeWidth={1.5} aria-hidden="true" />
              <p className="text-emerald-300 font-semibold text-xl">
                ¡Onboarding reiniciado!
              </p>
              <p className="text-slate-400">
                Redirigiendo al onboarding en 2 segundos...
              </p>
              <div className="flex justify-center">
                <div className="w-48 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 animate-pulse" style={{ width: '100%' }} />
                </div>
              </div>
            </div>
          )}

          {/* Info Box */}
          <div className="mt-8 p-4 bg-slate-800/50 rounded-lg text-left">
            <h3 className="text-sm font-semibold fi-text mb-2 flex items-center gap-2">
              <FolderOpen className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
              Datos Afectados:
            </h3>
            <ul className="fi-text-xs space-y-1 font-mono">
              <li>• fi_onboarding_progress</li>
              <li>• fi_onboarding_conversation</li>
              <li>• aurity_onboarding_completed</li>
              <li>• fi_onboarding_survey</li>
              <li>• aurity_desktop_setup_complete</li>
              <li>• aurity_fi_monitor_installed</li>
              <li className="text-cyan-400">• ~/.aurity/config/wizard-state.json (desktop)</li>
            </ul>
          </div>
        </div>
      </div>
    </AppTemplate>
  );
}
