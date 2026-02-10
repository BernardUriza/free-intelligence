'use client';

/**
 * Unauthorized Page
 * HIPAA Card: G-003 - Auth Integration
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
    <div className="auth-unauth-wrapper">
      <div className="auth-unauth-card">
        {/* Error Icon */}
        <div className="auth-unauth-icon-row">
          <div className="auth-unauth-icon-circle">
<AlertTriangle className="auth-unauth-icon-alert" />
          </div>
        </div>

        {/* Error Message */}
        <h1 className="fi-title-2xl auth-unauth-title-mb">
          Acceso No Autorizado
        </h1>
        <p className="auth-unauth-message">
          Tu rol actual <strong>({user?.email})</strong> no tiene permisos para acceder a esta página.
        </p>

        {/* Help Text */}
        <div className="auth-unauth-help-box">
          <h2 className="fi-title-sm auth-unauth-help-label-mb">¿Necesitas acceso?</h2>
          <p className="auth-unauth-help-text fi-text">
            Contacta al administrador del sistema para solicitar permisos adicionales.
          </p>
        </div>

        {/* Actions */}
        <div className="auth-unauth-actions">
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
