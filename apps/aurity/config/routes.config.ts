/**
 * Route Configuration - Defines access levels for all routes
 *
 * Route Types:
 * - public: No authentication required
 * - authenticated: Any logged-in user
 * - staff: Requires clinic membership (FI-staff, FI-doctor, FI-nurse, FI-admin)
 * - admin: Requires FI-admin or FI-superadmin
 * - superadmin: Requires FI-superadmin only
 */

import type { Role } from '@aurity-standalone/hooks/useRBAC';

export type RouteAccess = 'public' | 'authenticated' | 'staff' | 'admin' | 'superadmin';

export interface RouteConfig {
  /** Path pattern (supports wildcards like /admin/*) */
  path: string;
  /** Access level required */
  access: RouteAccess;
  /** Specific roles required (overrides access level) */
  roles?: Role[];
  /** Redirect path for unauthorized users */
  redirectTo?: string;
  /** Description for documentation */
  description?: string;
}

/**
 * Route definitions
 *
 * Order matters - first match wins
 * More specific routes should come before wildcards
 */
export const ROUTE_CONFIG: RouteConfig[] = [
  // ============================================================================
  // PUBLIC ROUTES - No authentication required
  // ============================================================================
  {
    path: '/',
    access: 'public',
    description: 'Landing/login page',
  },
  {
    path: '/callback',
    access: 'public',
    description: 'Auth0 callback',
  },
  {
    path: '/unauthorized',
    access: 'public',
    description: 'Access denied page',
  },
  {
    path: '/checkin/*',
    access: 'public',
    description: 'Patient check-in (kiosk mode)',
  },
  {
    path: '/receptionist/*',
    access: 'public',
    description: 'Receptionist TV display',
  },

  // ============================================================================
  // PUBLIC ROUTES - No authentication required
  // ============================================================================
  {
    path: '/',
    access: 'public',
    description: 'Landing/login page - accessible to all users',
  },
  {
    path: '/callback',
    access: 'public',
    description: 'Auth0 callback',
  },
  {
    path: '/unauthorized',
    access: 'public',
    description: 'Access denied page',
  },
  {
    path: '/checkin/*',
    access: 'public',
    description: 'Patient check-in (kiosk mode)',
  },
  {
    path: '/receptionist/*',
    access: 'public',
    description: 'Receptionist TV display',
  },
  {
    path: '/chat',
    access: 'public',
    description: 'Basic chat - available to all users (authenticated or not)',
  },

  // ============================================================================
  // AUTHENTICATED ROUTES - Any logged-in user (including random users)
  // ============================================================================
  {
    path: '/profile',
    access: 'authenticated',
    description: 'User profile',
  },

  // ============================================================================
  // STAFF ROUTES - Requires clinic membership
  // ============================================================================
  {
    path: '/dashboard',
    access: 'staff',
    description: 'Main dashboard',
  },
  {
    path: '/timeline',
    access: 'staff',
    description: 'Timeline/memory view',
  },
  {
    path: '/medical-ai/*',
    access: 'staff',
    description: 'Medical AI tools',
  },
  {
    path: '/viewer/*',
    access: 'staff',
    description: 'Document viewer',
  },
  {
    path: '/audit',
    access: 'staff',
    description: 'Audit logs',
  },
  {
    path: '/demo/*',
    access: 'staff',
    description: 'Demo pages',
  },

  // ============================================================================
  // ADMIN ROUTES - Requires FI-admin or FI-superadmin
  // ============================================================================
  {
    path: '/admin/clinics',
    access: 'admin',
    description: 'Clinic management',
  },
  {
    path: '/admin/users',
    access: 'superadmin',
    description: 'User management (superadmin only)',
  },
  {
    path: '/admin/*',
    access: 'admin',
    description: 'Admin pages',
  },
  {
    path: '/config',
    access: 'admin',
    description: 'System configuration',
  },
  {
    path: '/policy',
    access: 'admin',
    description: 'Policy viewer',
  },
  {
    path: '/infra',
    access: 'superadmin',
    description: 'Infrastructure (superadmin only)',
  },

  // ============================================================================
  // ONBOARDING - Special case (authenticated but guided)
  // ============================================================================
  {
    path: '/onboarding/*',
    access: 'authenticated',
    description: 'Onboarding flow',
  },
];

/**
 * Get route config for a given path
 */
export function getRouteConfig(path: string): RouteConfig | undefined {
  // Normalize path
  const normalizedPath = path.split('?')[0]; // Remove query string

  for (const route of ROUTE_CONFIG) {
    if (matchRoute(route.path, normalizedPath)) {
      return route;
    }
  }

  return undefined;
}

/**
 * Check if a path matches a route pattern
 */
function matchRoute(pattern: string, path: string): boolean {
  // Exact match
  if (pattern === path) {
    return true;
  }

  // Wildcard match
  if (pattern.endsWith('/*')) {
    const base = pattern.slice(0, -2);
    return path === base || path.startsWith(base + '/');
  }

  return false;
}

/**
 * Get required roles for a route access level
 */
export function getRequiredRoles(access: RouteAccess): Role[] {
  switch (access) {
    case 'public':
    case 'authenticated':
      return [];
    case 'staff':
      return ['FI-staff', 'FI-doctor', 'FI-nurse', 'FI-admin', 'FI-superadmin'];
    case 'admin':
      return ['FI-admin', 'FI-superadmin'];
    case 'superadmin':
      return ['FI-superadmin'];
    default:
      return [];
  }
}

/**
 * Check if a route is public
 */
export function isPublicRoute(path: string): boolean {
  const config = getRouteConfig(path);
  return config?.access === 'public';
}

/**
 * Get default redirect for a user based on their roles
 */
export function getDefaultRedirect(roles: Role[], isSuperAdmin: boolean): string {
  if (isSuperAdmin) {
    return '/dashboard';
  }

  if (roles.includes('FI-admin')) {
    return '/dashboard';
  }

  if (roles.includes('FI-doctor') || roles.includes('FI-nurse') || roles.includes('FI-staff')) {
    return '/dashboard';
  }

  // Random user with no special roles
  return '/chat';
}
