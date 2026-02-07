/**
 * @aurity-standalone/auth
 * 
 * Type-safe role-based access control utilities for healthcare applications.
 * 
 * @module @aurity-standalone/auth
 * @version 0.1.0
 * @license MIT
 */

/**
 * User roles in the healthcare system
 */
export type Role = 'FI-superadmin' | 'FI-clinician';

/**
 * JWT token claims structure
 */
export interface TokenClaims {
  /** User ID from JWT (e.g., "user-123456") */
  sub: string;
  /** Array of roles assigned to the user */
  roles?: Role[];
  /** Optional email for display purposes */
  email?: string;
  /** Optional name for display purposes */
  name?: string;
}

/**
 * Check if user has a specific role
 * 
 * @param claims - JWT token claims containing user information
 * @param role - Role to check (e.g., 'FI-clinician')
 * @returns true if user has the specified role
 * 
 * @example
 * ```typescript
 * const claims = { sub: 'user-123', roles: ['FI-clinician'] };
 * if (hasRole(claims, 'FI-clinician')) {
 *   console.log('User is a clinician');
 * }
 * ```
 */
export function hasRole(claims: TokenClaims, role: Role): boolean {
  return Array.isArray(claims.roles) && claims.roles.includes(role);
}

/**
 * Get all roles from token claims
 * 
 * @param claims - JWT token claims containing user information
 * @returns Array of roles (empty if none assigned)
 * 
 * @example
 * ```typescript
 * const claims = { sub: 'user-123', roles: ['FI-clinician'] };
 * const roles = getRoles(claims);
 * console.log(roles); // ['FI-clinician']
 * ```
 */
export function getRoles(claims: TokenClaims): Role[] {
  return Array.isArray(claims.roles) ? claims.roles : [];
}

/**
 * Check if user has any of the specified roles
 * 
 * @param claims - JWT token claims
 * @param roles - Array of roles to check
 * @returns true if user has at least one of the roles
 * 
 * @example
 * ```typescript
 * const claims = { sub: 'user-123', roles: ['FI-clinician'] };
 * if (hasAnyRole(claims, ['FI-clinician', 'FI-superadmin'])) {
 *   console.log('User has medical access');
 * }
 * ```
 */
export function hasAnyRole(claims: TokenClaims, roles: Role[]): boolean {
  const userRoles = getRoles(claims);
  return roles.some(role => userRoles.includes(role));
}

/**
 * Check if user has all of the specified roles
 * 
 * @param claims - JWT token claims
 * @param roles - Array of roles to check
 * @returns true if user has all of the roles
 * 
 * @example
 * ```typescript
 * const claims = { sub: 'user-123', roles: ['FI-clinician', 'FI-superadmin'] };
 * if (hasAllRoles(claims, ['FI-clinician', 'FI-superadmin'])) {
 *   console.log('User is a super clinician');
 * }
 * ```
 */
export function hasAllRoles(claims: TokenClaims, roles: Role[]): boolean {
  const userRoles = getRoles(claims);
  return roles.every(role => userRoles.includes(role));
}
