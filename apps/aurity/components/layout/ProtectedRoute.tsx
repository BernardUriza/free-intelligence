'use client';

/**
 * ProtectedRoute Component
 * HIPAA Card: G-003 - Auth0 Integration
 *
 * Protects routes by requiring authentication and specific roles/permissions.
 * Uses centralized RBAC hook for role management.
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { useEffect, ReactNode } from 'react';
import { useRBAC, type Role } from '@aurity-standalone/hooks/useRBAC';

interface ProtectedRouteProps {
  children: ReactNode;
  requireRoles?: Role[];
}

export function ProtectedRoute({ children, requireRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading: authLoading, loginWithRedirect, user } = useAuth();
  const { hasAnyRole, isSuperAdmin, isLoading: rbacLoading } = useRBAC();
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      // Wait for Auth0 to finish loading
      if (authLoading || rbacLoading) return;

      // Redirect to login if not authenticated
      if (!isAuthenticated) {
        loginWithRedirect({
          appState: {
            returnTo: window.location.pathname,
          },
        });
        return;
      }

      console.log('[ProtectedRoute] User authenticated:', user?.email);

      // Superadmin bypass (handled by useRBAC hook)
      if (isSuperAdmin) {
        console.log('[ProtectedRoute] [SUPERADMIN] Full access granted');
        return;
      }

      // Check role requirements if specified
      if (requireRoles && requireRoles.length > 0) {
        console.log('[ProtectedRoute] Required roles:', requireRoles);

        if (!hasAnyRole(requireRoles)) {
          console.warn('[ProtectedRoute] Access denied - missing required roles');
          router.push('/unauthorized');
          return;
        }

        console.log('[ProtectedRoute] [OK] Access granted');
      }
    };

    checkAuth();
  }, [isAuthenticated, authLoading, rbacLoading, loginWithRedirect, requireRoles, hasAnyRole, isSuperAdmin, router, user]);

  // Show loading state while checking authentication
  if (authLoading || rbacLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          {/* Animated spinner */}
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
          </div>

          {/* Loading text */}
          <h1 className="fi-title-2xl mb-2">Verificando autenticación...</h1>
          <p className="text-slate-400">Por favor espera</p>
        </div>
      </div>
    );
  }

  // Show nothing while redirecting
  if (!isAuthenticated) {
    return null;
  }

  // Render protected content
  return <>{children}</>;
}
