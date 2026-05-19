/**
 * useConfigPage Hook
 *
 * Centralises auth gating, RBAC enforcement, modal toggles,
 * and the onboarding-reset handler for the ConfigPage.
 *
 * SRP: state + side-effects only — zero rendering.
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import { confirmDanger, showSuccess, showError } from '@/lib/swal';
import { ONBOARDING_STORAGE_KEYS } from './constants';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ConfigPage');

export function useConfigPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { isSuperAdmin, isLoading: rbacLoading, roles } = useRBAC();
  const router = useRouter();

  // --- Derived ---
  const isLoading = authLoading || rbacLoading;

  // --- UI State ---
  const [resettingOnboarding, setResettingOnboarding] = useState(false);
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [showRolesModal, setShowRolesModal] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);

  // --- Access guard ---
  useEffect(() => {
    if (!isLoading && isAuthenticated && !isSuperAdmin) {
      log.warn('Access denied - not superadmin');
      router.push('/unauthorized');
    }
  }, [isLoading, isAuthenticated, isSuperAdmin, router]);

  // --- Handlers ---
  const handleResetOnboarding = useCallback(async () => {
    const confirmed = await confirmDanger({
      title: '¿Reiniciar onboarding?',
      text: 'Esto eliminará todo el progreso guardado.',
      confirmText: 'Reiniciar',
    });
    if (!confirmed) return;

    setResettingOnboarding(true);

    try {
      for (const key of ONBOARDING_STORAGE_KEYS) {
        localStorage.removeItem(key);
      }

      log.info('Onboarding reset successfully');
      await showSuccess('Onboarding reiniciado', 'Redirigiendo...');
      router.push('/onboarding');
    } catch (error) {
      log.error('Failed to reset onboarding', { error: String(error) });
      await showError('Error', 'No se pudo reiniciar el onboarding');
    } finally {
      setResettingOnboarding(false);
    }
  }, [router]);

  return {
    // Auth / access
    user,
    isAuthenticated,
    isSuperAdmin,
    isLoading,
    roles,

    // Onboarding reset
    resettingOnboarding,
    handleResetOnboarding,

    // Modal toggles
    showUserManagement,
    setShowUserManagement,
    showRolesModal,
    setShowRolesModal,
    showAuditModal,
    setShowAuditModal,
  } as const;
}
