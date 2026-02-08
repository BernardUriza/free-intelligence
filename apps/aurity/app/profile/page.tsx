'use client';

/**
 * User Profile Page
 * Shows user information and settings
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { profileHeader } from '@/config/page-headers';
import { showSuccess, showError } from '@/lib/swal';
import { CheckCircle2, Trash2, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [diskUsage, setDiskUsage] = useState<{ used: string; total: string; percent: number } | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // All users use email/password auth (no social login)
  const isSocialLogin = false;

  // Callback declared before useEffect that uses it
  const fetchDiskUsage = useCallback(async () => {
    try {
      const data = await api.get<{ used: string; total: string; percent: number }>(
        `${ROUTES.system}/disk-usage`
      );
      setDiskUsage(data);
    } catch (error) {
      console.error('Error fetching disk usage:', error);
    }
  }, []);

  // Fetch disk usage on mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchDiskUsage();
    }
  }, [isAuthenticated, fetchDiskUsage]);

  // Handlers for profile actions
  const handleChangePassword = () => {
    // TODO: Implement change password endpoint (POST /auth/change-password)
    alert('Cambio de contraseña no disponible aún. Contacta al administrador.');
  };

  const handleDeleteLongitudinalMemory = async () => {
    setIsDeleting(true);
    try {
      const userId = encodeURIComponent(user?.sub || 'unknown');
      const result = await api.post<{ message: string }>(
        `${ROUTES.system}/clear-memory?user_id=${userId}`
      );

      // Clear ChatWidget localStorage
      // The ChatWidget stores messages with keys like 'chat_messages', 'chat_history', etc.
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
      // Refresh disk usage
      await fetchDiskUsage();

      // Force refresh chat widget if it's open (trigger storage event)
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'chat_messages',
        oldValue: 'cleared',
        newValue: null,
        url: window.location.href
      }));
    } catch (error) {
      console.error('Error deleting memory:', error);
      await showError('Error de red', error instanceof Error ? error.message : 'No se pudo conectar al servidor');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="layout-loading-screen">
        <div className="prof-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="layout-loading-screen">
        <div className="prof-unauth-wrapper">
          <p className="prof-unauth-text">Debes iniciar sesión para ver tu perfil</p>
          <Link href="/" className="fi-text-primary prof-unauth-link">
            Volver al inicio
          </Link>
        </div>
      </div>
    );
  }

  // Generate header config with user data
  const headerConfig = profileHeader({
    email: user?.email,
    emailVerified: user?.email_verified,
    role: user?.roles?.[0] || 'USER',
  });

  return (
    <AppTemplate headerConfig={headerConfig} showWatermark={true} showGeometricBg={true}>

      {/* Main Content */}
      <main className="prof-main">
        {/* Profile Card */}
        <div className="prof-card">
          {/* Header with Avatar */}
          <div className="prof-card-header">
            <div className="prof-avatar-row">
              {user?.picture ? (
                <img
                  src={user.picture}
                  alt={user.name || 'User'}
                  className="prof-avatar-img"
                />
              ) : (
                <div className="fi-avatar-lg prof-avatar-fallback">
                  <Image
                    src="/logo.svg"
                    alt="Aurity Logo"
                    width={64}
                    height={64}
                    className="prof-avatar-logo"
                  />
                </div>
              )}
              <div>
                <h2 className="fi-title-2xl">{user?.name || 'Usuario'}</h2>
                <p className="prof-email">{user?.email}</p>
                {user?.email_verified && (
                  <div className="prof-verified-row">
                    <CheckCircle2 className="fi-icon-sm prof-verified-icon" />
                    <span className="prof-verified-text fi-text-green">Email verificado</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Profile Information */}
          <div className="prof-info-content">
            {/* Account Information */}
            <div>
              <h3 className="fi-title prof-info-title">Información de la Cuenta</h3>
              <div className="fi-stack-md">
                <div className="prof-info-row fi-border-bottom">
                  <span className="prof-label">Nombre</span>
                  <span className="prof-value">{user?.name || 'No disponible'}</span>
                </div>
                <div className="prof-info-row fi-border-bottom">
                  <span className="prof-label">Email</span>
                  <span className="prof-value">{user?.email || 'No disponible'}</span>
                </div>
                <div className="prof-info-row fi-border-bottom">
                  <span className="prof-label">Nickname</span>
                  <span className="prof-value">{user?.nickname || 'No disponible'}</span>
                </div>
                <div className="prof-info-row fi-border-bottom">
                  <span className="prof-label">Última actualización</span>
                  <span className="prof-value">
                    {user?.updated_at ? new Date(user.updated_at).toLocaleDateString('es-MX') : 'No disponible'}
                  </span>
                </div>
              </div>
            </div>

            {/* User Metadata */}
            {user && Object.keys(user).length > 0 && (
              <div>
                <h3 className="fi-title prof-info-title">Datos Adicionales</h3>
                <div className="prof-metadata-block">
                  <pre className="fi-text-xs prof-metadata-pre">
                    {JSON.stringify(user, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Settings Section */}
        <div className="prof-section">
          <h3 className="fi-title prof-section-title">Configuración</h3>
          <p className="prof-section-desc">
            Para cambiar tu información de perfil, contacta al administrador.
          </p>
          <div className="prof-button-row">
            {!isSocialLogin && (
              <Button 
                variant="secondary" 
                size="sm"
                onClick={handleChangePassword}
              >
                Cambiar contraseña
              </Button>
            )}
          </div>
        </div>

        {/* Disk Usage Section */}
        <div className="prof-section">
          <h3 className="fi-title prof-section-title">Estado del Almacenamiento</h3>
          {diskUsage ? (
            <div className="fi-stack-md">
              <div className="prof-disk-row">
                <span className="prof-disk-label">Usado</span>
                <span className="prof-disk-value">{diskUsage.used}</span>
              </div>
              <div className="prof-disk-track">
                <div 
                  className={diskUsage.percent > 80 ? 'layout-progress-critical' : diskUsage.percent > 60 ? 'layout-progress-warning' : 'layout-progress-healthy'}
                  style={{ width: `${Math.min(diskUsage.percent, 100)}%` }}
                />
              </div>
              <div className="prof-disk-row">
                <span className="prof-disk-label">Total disponible</span>
                <span className="prof-disk-value">{diskUsage.total}</span>
              </div>
            </div>
          ) : (
            <p className="prof-disk-loading">Cargando información del disco...</p>
          )}
        </div>

        {/* Danger Zone */}
        <div className="prof-danger-zone">
          <h3 className="prof-danger-title fi-text-error">Zona Peligrosa</h3>
          <p className="prof-danger-desc">
            Estas acciones son irreversibles. Los datos eliminados no se pueden recuperar.
          </p>
          <Button 
            variant="danger" 
            size="sm"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 className="prof-icon-sm" strokeWidth={1.5} aria-hidden="true" />
            Borrar toda la memoria longitudinal
          </Button>
          <p className="prof-danger-footnote">
            Elimina todas las sesiones HDF5 y mensajes de chat. Configuraciones de personalidades y pacientes se mantienen.
          </p>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteModal && (
          <div className="prof-modal-overlay">
            <div className="prof-modal-content">
              <h3 className="prof-modal-title fi-text-error">
                <AlertTriangle className="prof-icon-md" strokeWidth={1.5} aria-hidden="true" />
                Confirmar eliminación
              </h3>
              <p className="fi-text prof-modal-body">
                Estás a punto de eliminar <strong>TODA la memoria longitudinal</strong>:
              </p>
              <ul className="prof-modal-list">
                <li>Todos los archivos HDF5 de sesiones</li>
                <li>Todos los mensajes de chat</li>
                <li>Historial de conversaciones</li>
              </ul>
              <p className="prof-modal-warning">
                <CheckCircle2 className="prof-modal-warning-icon" strokeWidth={1.5} aria-hidden="true" />
                Se mantendrán: configuraciones de personalidades y registros de pacientes
              </p>
              <p className="fi-text-error prof-modal-irreversible">
                Esta acción NO se puede deshacer.
              </p>
              <div className="prof-modal-actions">
                <Button 
                  variant="secondary" 
                  onClick={() => setShowDeleteModal(false)}
                  disabled={isDeleting}
                  className="prof-modal-btn"
                >
                  Cancelar
                </Button>
                <Button 
                  variant="danger" 
                  onClick={handleDeleteLongitudinalMemory}
                  disabled={isDeleting}
                  className="prof-modal-btn"
                >
                  {isDeleting ? 'Eliminando...' : 'Sí, eliminar todo'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>
    </AppTemplate>
  );
}
