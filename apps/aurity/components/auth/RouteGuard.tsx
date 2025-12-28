'use client';

/**
 * RouteGuard - Protects routes based on user roles and permissions
 *
 * Usage:
 * <RouteGuard requireAuth>
 *   <ProtectedContent />
 * </RouteGuard>
 *
 * <RouteGuard requireRoles={['FI-admin', 'FI-superadmin']}>
 *   <AdminContent />
 * </RouteGuard>
 *
 * <RouteGuard requireClinicMembership>
 *   <ClinicContent />
 * </RouteGuard>
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC, Role } from '@aurity-standalone/hooks/useRBAC';
import { Loader2 } from 'lucide-react';

interface RouteGuardProps {
  children: React.ReactNode;
  /** Require user to be authenticated */
  requireAuth?: boolean;
  /** Require user to have ANY of these roles */
  requireRoles?: Role[];
  /** Require user to have ALL of these roles */
  requireAllRoles?: Role[];
  /** Allow superadmin to bypass all checks */
  allowSuperadminBypass?: boolean;
  /** Require user to be linked to a clinic */
  requireClinicMembership?: boolean;
  /** Custom redirect path on unauthorized (default: /unauthorized) */
  unauthorizedRedirect?: string;
  /** Custom redirect path on unauthenticated (default: login) */
  unauthenticatedRedirect?: string;
  /** Show loading spinner while checking auth */
  showLoading?: boolean;
  /** Custom loading component */
  loadingComponent?: React.ReactNode;
}

export function RouteGuard({
  children,
  requireAuth = true,
  requireRoles,
  requireAllRoles,
  allowSuperadminBypass = true,
  requireClinicMembership = false,
  unauthorizedRedirect = '/unauthorized',
  unauthenticatedRedirect,
  showLoading = true,
  loadingComponent,
}: RouteGuardProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, loginWithRedirect } = useAuth();
  const { roles, isSuperAdmin, isLoading: rbacLoading, hasAnyRole, hasAllRoles } = useRBAC();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    // Wait for auth to load
    if (authLoading || rbacLoading) {
      return;
    }

    // Check authentication
    if (requireAuth && !isAuthenticated) {
      if (unauthenticatedRedirect) {
        router.push(unauthenticatedRedirect);
      } else {
        loginWithRedirect();
      }
      return;
    }

    // Superadmin bypass
    if (allowSuperadminBypass && isSuperAdmin) {
      setIsAuthorized(true);
      return;
    }

    // Check roles
    if (requireRoles && requireRoles.length > 0) {
      if (!hasAnyRole(requireRoles)) {
        router.push(unauthorizedRedirect);
        return;
      }
    }

    if (requireAllRoles && requireAllRoles.length > 0) {
      if (!hasAllRoles(requireAllRoles)) {
        router.push(unauthorizedRedirect);
        return;
      }
    }

    // All checks passed
    setIsAuthorized(true);
  }, [
    authLoading,
    rbacLoading,
    isAuthenticated,
    isSuperAdmin,
    roles,
    requireAuth,
    requireRoles,
    requireAllRoles,
    allowSuperadminBypass,
    requireClinicMembership,
    unauthorizedRedirect,
    unauthenticatedRedirect,
    router,
    loginWithRedirect,
    hasAnyRole,
    hasAllRoles,
  ]);

  // Loading state
  if (authLoading || rbacLoading || isAuthorized === null) {
    if (!showLoading) {
      return null;
    }

    if (loadingComponent) {
      return <>{loadingComponent}</>;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <Loader2 className="animate-spin h-12 w-12 text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Verificando permisos...</p>
        </div>
      </div>
    );
  }

  // Not authorized - redirect is handled in useEffect
  if (!isAuthorized) {
    return null;
  }

  // Authorized
  return <>{children}</>;
}

/**
 * Predefined guards for common use cases
 */

/** Requires any authenticated user */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  return <RouteGuard requireAuth>{children}</RouteGuard>;
}

/** Requires superadmin role */
export function SuperadminGuard({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard requireAuth allowSuperadminBypass={false} requireRoles={['FI-superadmin']}>
      {children}
    </RouteGuard>
  );
}

/** Requires admin or superadmin role */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard requireAuth requireRoles={['FI-admin', 'FI-superadmin']}>
      {children}
    </RouteGuard>
  );
}

/** Requires staff, doctor, admin, or superadmin role (clinic member) */
export function StaffGuard({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard requireAuth requireRoles={['FI-staff', 'FI-doctor', 'FI-nurse', 'FI-admin', 'FI-superadmin']}>
      {children}
    </RouteGuard>
  );
}
