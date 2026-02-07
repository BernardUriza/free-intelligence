export type Role = 'FI-superadmin' | 'FI-clinician';

export interface TokenClaims {
  sub: string;
  roles?: Role[];
}

export function hasRole(claims: TokenClaims, role: Role): boolean {
  return Array.isArray(claims.roles) && claims.roles.includes(role);
}

export function getRoles(claims: TokenClaims): Role[] {
  return Array.isArray(claims.roles) ? claims.roles : [];
}
