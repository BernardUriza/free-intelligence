'use client';

/**
 * Unauthorized Page
 * HIPAA Card: G-003 - Auth0 Integration
 *
 * Shown when user doesn't have required role permissions.
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { Home, LogOut, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function UnauthorizedPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="max-w-md w-full bg-red-900/20 border border-red-500/50 rounded-lg p-8">
        {/* Error Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center">
<AlertTriangle className="w-12 h-12 text-red-500" />
          </div>
        </div>

        {/* Error Message */}
        <h1 className="fi-title-2xl text-center mb-3">
          Acceso No Autorizado
        </h1>
        <p className="text-red-200 text-center mb-6">
          Tu rol actual <strong>({user?.email})</strong> no tiene permisos para acceder a esta página.
        </p>

        {/* Help Text */}
        <div className="bg-slate-800/50 rounded-lg p-4 mb-6">
          <h2 className="fi-title-sm mb-2">¿Necesitas acceso?</h2>
          <p className="text-sm fi-text">
            Contacta al administrador del sistema para solicitar permisos adicionales.
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          <Button
            onClick={() => router.push('/')}
            variant="primary"
            fullWidth
            icon={Home}
          >
            Volver al Inicio
          </Button>

          <Button
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            variant="secondary"
            fullWidth
            icon={LogOut}
          >
            Cambiar de Cuenta
          </Button>
        </div>
      </div>
    </div>
  );
}
