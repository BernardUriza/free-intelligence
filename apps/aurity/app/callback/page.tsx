'use client';

/**
 * Auth0 Callback Page
 * HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
 *
 * Handles Auth0 redirect after successful login.
 * Shows loading state while Auth0 processes the authentication.
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Home, AlertTriangle, Lock } from 'lucide-react';

export default function CallbackPage() {
  const { isLoading, isAuthenticated, error } = useAuth();
  const router = useRouter();

  useEffect(() => {
    console.log('[Callback] Auth state:', { isLoading, isAuthenticated, error });

    // Redirect to dashboard after successful authentication
    if (!isLoading && isAuthenticated) {
      console.log('[Callback] Redirecting to /dashboard');
      // Use replace instead of push to avoid back button issues
      router.replace('/dashboard');
    }
  }, [isLoading, isAuthenticated, router, error]);

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="max-w-md w-full bg-red-900/20 border border-red-500 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
<AlertTriangle className="w-8 h-8 text-red-500" />
            <h1 className="fi-title-xl">Error de Autenticación</h1>
          </div>
          <p className="text-red-200 mb-4">{error.message}</p>
          <Button
            onClick={() => router.push('/')}
            variant="danger"
            fullWidth
            icon={Home}
          >
            Volver al Inicio
          </Button>
        </div>
      </div>
    );
  }

  // Loading state
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="text-center">
        {/* Animated spinner */}
        <div className="relative w-24 h-24 mx-auto mb-6">
          <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
        </div>

        {/* Loading text */}
        <h1 className="fi-title-2xl mb-2">Autenticando...</h1>
        <p className="text-slate-400">Por favor espera mientras procesamos tu inicio de sesión</p>

        {/* Security indicator */}
        <div className="mt-8 flex items-center justify-center gap-2 text-sm fi-text-green">
<Lock className="w-4 h-4" />
          <span>Conexión segura con Auth0</span>
        </div>
      </div>
    </div>
  );
}
