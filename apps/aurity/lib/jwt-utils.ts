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
 * Type-safe JWT payload for self-hosted auth
 */
export interface JwtPayload {
  /** User ID */
  sub: string;

  /** Issued at timestamp */
  iat: number;

  /** Expiration timestamp */
  exp: number;

  /** User email */
  email: string;

  /** User roles */
  roles: string[];

  /** Clinic ID (optional) */
  clinic_id?: string;

  /** User display name */
  name?: string;

  /** Other claims */
  [key: string]: any;
}

/**
 * Extract roles from JWT token.
 *
 * @param token - JWT access token
 * @returns Array of role strings
 */
export function extractRolesFromToken(token: string): string[] {
  try {
    if (!token || token.split('.').length !== 3) {
      return [];
    }

    const payload = decodeJwtPayload<JwtPayload>(token);
    return payload.roles || [];
  } catch (error) {
    // Silent fail — return empty roles on decode error
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
    const payload = decodeJwtPayload<JwtPayload>(token);
    const now = Math.floor(Date.now() / 1000);
    return payload.exp < now;
  } catch {
    return true;
  }
}
