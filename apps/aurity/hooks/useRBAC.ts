/**
 * useRBAC Hook - Centralized Role-Based Access Control
 *
 * Integrates with Auth0 JWT roles and provides extensible RBAC
 * architecture for granular permission management.
 *
 * Architecture:
 * - Reads roles from Auth0 JWT token (https://aurity.app/roles)
 * - Supports superadmin override list (configurable via env)
 * - Provides declarative permission checks
 * - Caches token parsing for performance
 */

'use client';

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useState, useEffect, useMemo } from 'react';

// ============================================================================
// ROLE DEFINITIONS
// ============================================================================

export const ROLES = {
  SUPERADMIN: 'FI-superadmin',
  ADMIN: 'FI-admin',
  DOCTOR: 'FI-doctor',
  NURSE: 'FI-nurse',
  STAFF: 'FI-staff',
  VIEWER: 'FI-viewer',
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

// ============================================================================
// PERMISSION DEFINITIONS
// ============================================================================

export const PERMISSIONS = {
  // System administration
  MANAGE_SYSTEM: 'system:manage',
  VIEW_LOGS: 'system:logs',
  MANAGE_USERS: 'users:manage',
  VIEW_USERS: 'users:view',
  MANAGE_ROLES: 'roles:manage',

  // Clinical operations
  CREATE_SESSION: 'session:create',
  VIEW_SESSION: 'session:view',
  DELETE_SESSION: 'session:delete',
  EXPORT_DATA: 'data:export',

  // Configuration
  MANAGE_CONFIG: 'config:manage',
  VIEW_CONFIG: 'config:view',
  RESET_ONBOARDING: 'onboarding:reset',
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

// ============================================================================
// ROLE-PERMISSION MAPPING
// ============================================================================

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [ROLES.SUPERADMIN]: [
    // Superadmin has ALL permissions
    PERMISSIONS.MANAGE_SYSTEM,
    PERMISSIONS.VIEW_LOGS,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.VIEW_USERS,
    PERMISSIONS.MANAGE_ROLES,
    PERMISSIONS.CREATE_SESSION,
    PERMISSIONS.VIEW_SESSION,
    PERMISSIONS.DELETE_SESSION,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.MANAGE_CONFIG,
    PERMISSIONS.VIEW_CONFIG,
    PERMISSIONS.RESET_ONBOARDING,
  ],

  [ROLES.ADMIN]: [
    PERMISSIONS.VIEW_LOGS,
    PERMISSIONS.VIEW_USERS,
    PERMISSIONS.CREATE_SESSION,
    PERMISSIONS.VIEW_SESSION,
    PERMISSIONS.DELETE_SESSION,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.VIEW_CONFIG,
  ],

  [ROLES.DOCTOR]: [
    PERMISSIONS.CREATE_SESSION,
    PERMISSIONS.VIEW_SESSION,
    PERMISSIONS.EXPORT_DATA,
  ],

  [ROLES.NURSE]: [
    PERMISSIONS.CREATE_SESSION,
    PERMISSIONS.VIEW_SESSION,
  ],

  [ROLES.STAFF]: [
    PERMISSIONS.VIEW_SESSION,
  ],

  [ROLES.VIEWER]: [
    PERMISSIONS.VIEW_SESSION,
  ],
};

// ============================================================================
// SUPERADMIN CONFIGURATION
// ============================================================================

/**
 * Superadmin email list (configurable via environment variable)
 * IMPORTANT: Must set NEXT_PUBLIC_SUPERADMIN_EMAILS in .env.local
 */
const getSuperAdminEmails = (): string[] => {
  if (typeof window === 'undefined') return [];

  const envEmails = process.env.NEXT_PUBLIC_SUPERADMIN_EMAILS;
  if (envEmails) {
    return envEmails.split(',').map(email => email.trim().toLowerCase());
  }

  // No fallback - env var is required for security
  console.warn('⚠️ NEXT_PUBLIC_SUPERADMIN_EMAILS not set. No superadmins configured.');
  return [];
};

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export interface UseRBACReturn {
  /** User's roles from Auth0 */
  roles: Role[];

  /** Is user a superadmin (bypass all checks) */
  isSuperAdmin: boolean;

  /** Check if user has specific role */
  hasRole: (role: Role) => boolean;

  /** Check if user has ALL of the specified roles */
  hasAllRoles: (roles: Role[]) => boolean;

  /** Check if user has ANY of the specified roles */
  hasAnyRole: (roles: Role[]) => boolean;

  /** Check if user has specific permission */
  hasPermission: (permission: Permission) => boolean;

  /** Check if user has ALL of the specified permissions */
  hasAllPermissions: (permissions: Permission[]) => boolean;

  /** Check if user has ANY of the specified permissions */
  hasAnyPermission: (permissions: Permission[]) => boolean;

  /** Is RBAC data still loading */
  isLoading: boolean;

  /** All permissions user has (computed from roles) */
  permissions: Permission[];
}

export function useRBAC(): UseRBACReturn {
  const { user, isAuthenticated, isLoading: authLoading, getAccessTokenSilently } = useAuth();
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is superadmin via email
  const isSuperAdmin = useMemo(() => {
    if (!user?.email) return false;
    const superAdmins = getSuperAdminEmails();
    return superAdmins.includes(user.email.toLowerCase());
  }, [user?.email]);

  // Load roles from Auth0 JWT token
  useEffect(() => {
    const loadRoles = async () => {
      if (authLoading) return;

      if (!isAuthenticated || !user) {
        setRoles([]);
        setIsLoading(false);
        return;
      }

      // Superadmin bypass - automatically grant superadmin role
      if (isSuperAdmin) {
        setRoles([ROLES.SUPERADMIN]);
        setIsLoading(false);
        return;
      }

      try {
        // Extract roles from Auth0 JWT token
        const token = await getAccessTokenSilently({
          authorizationParams: {
            audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || 'https://app.aurity.io',
            scope: process.env.NEXT_PUBLIC_AUTH0_SCOPE || 'openid profile email',
          },
        });
        const { extractRolesFromToken } = await import('@/lib/jwt-utils');
        const userRoles = extractRolesFromToken(token);

        // Validate and cast roles
        const validRoles = userRoles.filter(role =>
          Object.values(ROLES).includes(role as Role)
        ) as Role[];

        setRoles(validRoles);
        setIsLoading(false);
      } catch (error) {
        console.error('[useRBAC] Failed to load roles:', error);
        // On error, assume no roles (safe default)
        setRoles([]);
        setIsLoading(false);
      }
    };

    loadRoles();
  }, [isAuthenticated, user, authLoading, getAccessTokenSilently, isSuperAdmin]);

  // Compute all permissions from roles
  const permissions = useMemo(() => {
    // Superadmin has all permissions
    if (isSuperAdmin) {
      return ROLE_PERMISSIONS[ROLES.SUPERADMIN];
    }

    // Combine permissions from all user roles (deduplicate)
    const allPermissions = new Set<Permission>();
    for (const role of roles) {
      const rolePermissions = ROLE_PERMISSIONS[role] || [];
      rolePermissions.forEach(p => allPermissions.add(p));
    }

    return Array.from(allPermissions);
  }, [roles, isSuperAdmin]);

  // Role checking functions
  const hasRole = (role: Role): boolean => {
    if (isSuperAdmin) return true;
    return roles.includes(role);
  };

  const hasAllRoles = (requiredRoles: Role[]): boolean => {
    if (isSuperAdmin) return true;
    return requiredRoles.every(role => roles.includes(role));
  };

  const hasAnyRole = (requiredRoles: Role[]): boolean => {
    if (isSuperAdmin) return true;
    return requiredRoles.some(role => roles.includes(role));
  };

  // Permission checking functions
  const hasPermission = (permission: Permission): boolean => {
    if (isSuperAdmin) return true;
    return permissions.includes(permission);
  };

  const hasAllPermissions = (requiredPermissions: Permission[]): boolean => {
    if (isSuperAdmin) return true;
    return requiredPermissions.every(p => permissions.includes(p));
  };

  const hasAnyPermission = (requiredPermissions: Permission[]): boolean => {
    if (isSuperAdmin) return true;
    return requiredPermissions.some(p => permissions.includes(p));
  };

  return {
    roles,
    isSuperAdmin,
    hasRole,
    hasAllRoles,
    hasAnyRole,
    hasPermission,
    hasAllPermissions,
    hasAnyPermission,
    isLoading,
    permissions,
  };
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get human-readable role name
 */
export function getRoleName(role: Role): string {
  const names: Record<Role, string> = {
    [ROLES.SUPERADMIN]: 'Superadministrador',
    [ROLES.ADMIN]: 'Administrador',
    [ROLES.DOCTOR]: 'Doctor',
    [ROLES.NURSE]: 'Enfermera',
    [ROLES.STAFF]: 'Personal',
    [ROLES.VIEWER]: 'Observador',
  };
  return names[role] || role;
}

/**
 * Get role badge color
 */
export function getRoleBadgeColor(role: Role): string {
  const colors: Record<Role, string> = {
    [ROLES.SUPERADMIN]: 'bg-purple-600',
    [ROLES.ADMIN]: 'bg-blue-600',
    [ROLES.DOCTOR]: 'bg-emerald-600',
    [ROLES.NURSE]: 'bg-cyan-600',
    [ROLES.STAFF]: 'bg-slate-600',
    [ROLES.VIEWER]: 'bg-gray-600',
  };
  return colors[role] || 'bg-gray-600';
}
