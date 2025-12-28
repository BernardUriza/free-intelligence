/**
 * Authentication Utilities (Extracted from @aurity/fi-auth)
 * 
 * Type-safe role-based access control utilities.
 * Standalone version - no external dependencies required.
 * 
 * @module lib/internal/auth
 */

export type Role = 'FI-superadmin' | 'FI-clinician' | 'FI-staff' | 'FI-patient';

export interface TokenClaims {
  sub: string;
  roles?: Role[];
}

/**
 * Check if user has a specific role
 * @param claims - JWT token claims
 * @param role - Role to check
 * @returns true if user has the role
 */
export function hasRole(claims: TokenClaims, role: Role): boolean {
  return Array.isArray(claims.roles) && claims.roles.includes(role);
}

/**
 * Get all roles from token claims
 * @param claims - JWT token claims
 * @returns Array of roles (empty if none)
 */
export function getRoles(claims: TokenClaims): Role[] {
  return Array.isArray(claims.roles) ? claims.roles : [];
}
