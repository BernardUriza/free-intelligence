'use client';

/**
 * Hook for profile page state and actions.
 * Manages disk usage fetching, password change, and memory deletion.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';
import { showSuccess, showError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';
import type { DiskUsage, ClearMemoryResponse } from '../types';

const log = createLogger('Profile');

export function useProfile() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [diskUsage, setDiskUsage] = useState<DiskUsage | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchDiskUsage = useCallback(async () => {
    try {
      const data = await api.get<DiskUsage>(`${ROUTES.system}/disk-usage`);
      setDiskUsage(data);
    } catch (error) {
      log.error('Failed to fetch disk usage', { error: String(error) });
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDiskUsage();
    }
  }, [isAuthenticated, fetchDiskUsage]);

  const handleChangePassword = useCallback(() => {
    alert('Cambio de contraseña no disponible aún. Contacta al administrador.');
  }, []);

  const handleDeleteLongitudinalMemory = useCallback(async () => {
    setIsDeleting(true);
    try {
      const userId = encodeURIComponent(user?.sub || 'unknown');
      const result = await api.post<ClearMemoryResponse>(
        `${ROUTES.system}/clear-memory?user_id=${userId}`
      );

      // Clear ChatWidget localStorage
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.startsWith('chat_') || key.startsWith('aurity_chat_'))) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));

      await showSuccess('Memoria eliminada', `${result.message}\n\nTambién se limpió el caché local del chat.`);
      setShowDeleteModal(false);
      await fetchDiskUsage();

      // Force refresh chat widget if open
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'chat_messages',
        oldValue: 'cleared',
        newValue: null,
        url: window.location.href
      }));
    } catch (error) {
      log.error('Failed to delete memory', { error: String(error) });
      await showError('Error de red', error instanceof Error ? error.message : 'No se pudo conectar al servidor');
    } finally {
      setIsDeleting(false);
    }
  }, [user?.sub, fetchDiskUsage]);

  return {
    user,
    isAuthenticated,
    isLoading,
    diskUsage,
    showDeleteModal,
    setShowDeleteModal,
    isDeleting,
    handleChangePassword,
    handleDeleteLongitudinalMemory,
  };
}
