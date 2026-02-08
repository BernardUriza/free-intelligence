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
import { gradients } from '@/lib/styles/gradients';
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
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-blue-400 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400 mb-4">Debes iniciar sesión para ver tu perfil</p>
          <Link href="/" className="fi-text-primary hover:text-blue-300">
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
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Profile Card */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
          {/* Header with Avatar */}
          <div className={`${gradients.primarySubtle} px-6 py-8`}>
            <div className="flex items-center gap-4">
              {user?.picture ? (
                <img
                  src={user.picture}
                  alt={user.name || 'User'}
                  className="w-20 h-20 rounded-full ring-4 ring-slate-700"
                />
              ) : (
                <div className="fi-avatar-lg ring-4 ring-slate-700 p-3">
                  <Image
                    src="/logo.svg"
                    alt="Aurity Logo"
                    width={64}
                    height={64}
                    className="w-full h-full"
                  />
                </div>
              )}
              <div>
                <h2 className="fi-title-2xl">{user?.name || 'Usuario'}</h2>
                <p className="text-slate-400">{user?.email}</p>
                {user?.email_verified && (
                  <div className="flex items-center gap-1 mt-2">
                    <CheckCircle2 className="fi-icon-sm text-green-500" />
                    <span className="text-sm fi-text-green">Email verificado</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Profile Information */}
          <div className="p-6 space-y-6">
            {/* Account Information */}
            <div>
              <h3 className="fi-title mb-4">Información de la Cuenta</h3>
              <div className="fi-stack-md">
                <div className="flex justify-between py-3 fi-border-bottom">
                  <span className="text-slate-400">Nombre</span>
                  <span className="text-white font-medium">{user?.name || 'No disponible'}</span>
                </div>
                <div className="flex justify-between py-3 fi-border-bottom">
                  <span className="text-slate-400">Email</span>
                  <span className="text-white font-medium">{user?.email || 'No disponible'}</span>
                </div>
                <div className="flex justify-between py-3 fi-border-bottom">
                  <span className="text-slate-400">Nickname</span>
                  <span className="text-white font-medium">{user?.nickname || 'No disponible'}</span>
                </div>
                <div className="flex justify-between py-3 fi-border-bottom">
                  <span className="text-slate-400">Última actualización</span>
                  <span className="text-white font-medium">
                    {user?.updated_at ? new Date(user.updated_at).toLocaleDateString('es-MX') : 'No disponible'}
                  </span>
                </div>
              </div>
            </div>

            {/* User Metadata */}
            {user && Object.keys(user).length > 0 && (
              <div>
                <h3 className="fi-title mb-4">Datos Adicionales</h3>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <pre className="fi-text-xs overflow-auto max-h-64">
                    {JSON.stringify(user, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Settings Section */}
        <div className="mt-6 bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="fi-title mb-4">Configuración</h3>
          <p className="text-slate-400 text-sm mb-4">
            Para cambiar tu información de perfil, contacta al administrador.
          </p>
          <div className="flex flex-wrap gap-3">
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
        <div className="mt-6 bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="fi-title mb-4">Estado del Almacenamiento</h3>
          {diskUsage ? (
            <div className="fi-stack-md">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Usado</span>
                <span className="text-white font-medium">{diskUsage.used}</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all ${
                    diskUsage.percent > 80 ? 'bg-red-500' : 
                    diskUsage.percent > 60 ? 'bg-yellow-500' : 
                    'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(diskUsage.percent, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Total disponible</span>
                <span className="text-white font-medium">{diskUsage.total}</span>
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Cargando información del disco...</p>
          )}
        </div>

        {/* Danger Zone */}
        <div className="mt-6 bg-red-950/20 border border-red-900/50 rounded-lg p-6">
          <h3 className="text-lg font-semibold fi-text-error mb-2">Zona Peligrosa</h3>
          <p className="text-slate-400 text-sm mb-4">
            Estas acciones son irreversibles. Los datos eliminados no se pueden recuperar.
          </p>
          <Button 
            variant="danger" 
            size="sm"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
            Borrar toda la memoria longitudinal
          </Button>
          <p className="text-slate-500 text-xs mt-2">
            Elimina todas las sesiones HDF5 y mensajes de chat. Configuraciones de personalidades y pacientes se mantienen.
          </p>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-800 border border-red-900/50 rounded-lg max-w-md w-full p-6">
              <h3 className="text-xl font-bold fi-text-error mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" strokeWidth={1.5} aria-hidden="true" />
                Confirmar eliminación
              </h3>
              <p className="fi-text mb-4">
                Estás a punto de eliminar <strong>TODA la memoria longitudinal</strong>:
              </p>
              <ul className="text-slate-400 text-sm space-y-2 mb-6 list-disc list-inside">
                <li>Todos los archivos HDF5 de sesiones</li>
                <li>Todos los mensajes de chat</li>
                <li>Historial de conversaciones</li>
              </ul>
              <p className="text-yellow-400 text-sm mb-6 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
                Se mantendrán: configuraciones de personalidades y registros de pacientes
              </p>
              <p className="fi-text-error font-bold mb-6">
                Esta acción NO se puede deshacer.
              </p>
              <div className="flex gap-3">
                <Button 
                  variant="secondary" 
                  onClick={() => setShowDeleteModal(false)}
                  disabled={isDeleting}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button 
                  variant="danger" 
                  onClick={handleDeleteLongitudinalMemory}
                  disabled={isDeleting}
                  className="flex-1"
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
