/**
 * JWT Utilities - Safe JWT token decoding
 *
 * JWT tokens use base64url encoding (RFC 4648), which differs from standard base64:
 * - base64url uses: - and _ (URL-safe)
 * - base64 uses: + and /
 *
 * This utility converts base64url to base64 before decoding.
 */

/**
 * Decodes JWT payload safely, handling base64url encoding.
 *
 * @param token - JWT token string (header.payload.signature)
 * @returns Decoded payload object
 * @throws Error if token is invalid or decoding fails
 *
 * @example
 * const payload = decodeJwtPayload(token);
 * const roles = payload['https://aurity.app/roles'] || [];
 */
export function decodeJwtPayload<T = Record<string, any>>(token: string): T {
  try {
    // Extract payload (second part of JWT)
    const parts = token.split('.');

    if (parts.length !== 3) {
      throw new Error('Invalid JWT format: expected 3 parts (header.payload.signature)');
    }

    const base64Url = parts[1];

    // Convert base64url to base64
    // - Replace - with +
    // - Replace _ with /
    // - Pad with = if needed (base64url omits padding)
    const base64 = base64Url
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    // Add padding if needed (base64 requires length to be multiple of 4)
    const paddedBase64 = base64.padEnd(
      base64.length + (4 - (base64.length % 4)) % 4,
      '='
    );

    // Decode base64 to string
    const jsonPayload = atob(paddedBase64);

    // Parse JSON
    return JSON.parse(jsonPayload) as T;

  } catch (error) {
    // Re-throw with context
    if (error instanceof Error) {
      throw new Error(`Failed to decode JWT payload: ${error.message}`);
    }
    throw new Error('Failed to decode JWT payload: Unknown error');
  }
}

/**
 * Type-safe JWT payload with Auth0 custom claims
 */
export interface Auth0JwtPayload {
  /** Auth0 user ID */
  sub: string;

  /** Issued at timestamp */
  iat: number;

  /** Expiration timestamp */
  exp: number;

  /** Audience */
  aud: string | string[];

  /** Issuer */
  iss: string;

  /** Custom: User roles (RBAC) */
  'https://aurity.app/roles'?: string[];

  /** Custom: User permissions */
  'https://aurity.app/permissions'?: string[];

  /** Other standard JWT claims */
  [key: string]: any;
}

/**
 * Extract roles from Auth0 JWT token.
 *
 * Handles both real JWT tokens (production) and mock tokens (development).
 *
 * @param token - JWT access token from Auth0 (or mock token in dev)
 * @returns Array of role strings (empty if no roles claim or mock token)
 *
 * @example
 * const roles = extractRolesFromToken(token);
 * if (roles.includes('FI-superadmin')) {
 *   // User is superadmin
 * }
 */
export function extractRolesFromToken(token: string): string[] {
  try {
    // Check if token looks like a JWT (has 3 parts separated by dots)
    if (!token || token.split('.').length !== 3) {
      console.warn('[jwt-utils] Token is not a JWT format (likely MockAuth0Provider in dev mode), returning empty roles');
      return [];
    }

    const payload = decodeJwtPayload<Auth0JwtPayload>(token);
    return payload['https://aurity.app/roles'] || [];
  } catch (error) {
    console.error('[jwt-utils] Failed to extract roles:', error);
    return [];
  }
}

/**
 * Check if token is expired.
 *
 * @param token - JWT token
 * @returns true if token is expired
 */
export function isTokenExpired(token: string): boolean {
  try {
    const payload = decodeJwtPayload<Auth0JwtPayload>(token);
    const now = Math.floor(Date.now() / 1000);
    return payload.exp < now;
  } catch {
    // If can't decode, assume expired (safe default)
    return true;
  }
}
