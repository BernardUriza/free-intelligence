'use client';

/**
 * ProtectedLayout - Automatically protects pages based on route config
 *
 * Usage in layout.tsx:
 * <ProtectedLayout>
 *   {children}
 * </ProtectedLayout>
 *
 * This component reads the current path and applies the appropriate
 * access control based on routes.config.ts
 */

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import { Loader2 } from 'lucide-react';
import {
  getRouteConfig,
  getRequiredRoles,
  isPublicRoute,
} from '@/config/routes.config';
import { isDesktop } from '@/lib/config/deployment';

interface ProtectedLayoutProps {
  children: React.ReactNode;
}

export function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, loginWithRedirect } = useAuth();
  const { roles, isSuperAdmin, isLoading: rbacLoading, hasAnyRole } = useRBAC();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    // In desktop mode, skip authentication requirements
    // Desktop uses license-based access, not Auth0
    if (isDesktop()) {
      setIsAuthorized(true);
      return;
    }

    // Public routes never need auth - skip all checks
    if (isPublicRoute(pathname)) {
      setIsAuthorized(true);
      return;
    }

    // Wait for auth to load (only for non-public routes)
    if (authLoading || rbacLoading) {
      return;
    }

    // Get route config
    const routeConfig = getRouteConfig(pathname);

    // No config found - allow (fallback to authenticated)
    if (!routeConfig) {
      if (!isAuthenticated) {
        loginWithRedirect();
        return;
      }
      setIsAuthorized(true);
      return;
    }

    // Public route - always allow
    if (routeConfig.access === 'public') {
      setIsAuthorized(true);
      return;
    }

    // Authenticated route - just need to be logged in
    if (routeConfig.access === 'authenticated') {
      if (!isAuthenticated) {
        loginWithRedirect();
        return;
      }
      setIsAuthorized(true);
      return;
    }

    // Protected route - need authentication first
    if (!isAuthenticated) {
      loginWithRedirect();
      return;
    }

    // Superadmin bypass for all non-public routes
    if (isSuperAdmin) {
      setIsAuthorized(true);
      return;
    }

    // Check required roles
    const requiredRoles = routeConfig.roles || getRequiredRoles(routeConfig.access);

    if (requiredRoles.length > 0 && !hasAnyRole(requiredRoles)) {
      // User doesn't have required role - redirect to unauthorized
      router.push(routeConfig.redirectTo || '/unauthorized');
      return;
    }

    // All checks passed
    setIsAuthorized(true);
  }, [
    pathname,
    authLoading,
    rbacLoading,
    isAuthenticated,
    isSuperAdmin,
    roles,
    router,
    loginWithRedirect,
    hasAnyRole,
  ]);

  // =========================================================================
  // RENDER: Public routes render immediately (no auth check needed)
  // =========================================================================
  // This MUST be checked BEFORE the loading state to avoid redirect flicker
  if (isPublicRoute(pathname)) {
    return <>{children}</>;
  }

  // Loading state for protected routes only
  if (authLoading || rbacLoading || isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <Loader2 className="animate-spin h-12 w-12 text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Verificando acceso...</p>
        </div>
      </div>
    );
  }

  // Not authorized - redirect is handled in useEffect
  if (!isAuthorized) {
    return null;
  }

  return <>{children}</>;
}
