/**
 * Route Configuration - Defines access levels for all routes
 *
 * Route Types:
 * - public: No authentication required
 * - authenticated: Any logged-in user
 * - staff: Requires FI-clinician or FI-superadmin
 * - admin: Requires FI-superadmin
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
    description: 'Landing/login page - accessible to all users',
  },
  {
    path: '/login',
    access: 'public',
    description: 'Login page',
  },
  {
    path: '/register',
    access: 'public',
    description: 'Registration page',
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
  {
    path: '/downloads',
    access: 'public',
    description: 'Desktop app downloads - public access for anyone to download',
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
  // ADMIN ROUTES - Requires FI-superadmin
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
  // ONBOARDING - Public (no auth required for first-time users)
  // ============================================================================
  {
    path: '/onboarding',
    access: 'public',
    description: 'Conversational onboarding flow',
  },
  {
    path: '/onboarding/*',
    access: 'public',
    description: 'Onboarding sub-routes (reset, etc.)',
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
  // Normalize: remove trailing slash for comparison (except for root "/")
  const normalize = (p: string) => (p.length > 1 && p.endsWith('/') ? p.slice(0, -1) : p);
  const normalizedPattern = normalize(pattern);
  const normalizedPath = normalize(path);

  // Exact match (with normalized paths)
  if (normalizedPattern === normalizedPath) {
    return true;
  }

  // Wildcard match
  if (pattern.endsWith('/*')) {
    const base = pattern.slice(0, -2);
    return normalizedPath === base || path.startsWith(base + '/');
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
      return ['FI-clinician', 'FI-superadmin'];
    case 'admin':
      return ['FI-superadmin'];
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
  if (isSuperAdmin || roles.includes('FI-clinician')) {
    return '/dashboard';
  }

  return '/chat';
}
