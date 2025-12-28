'use client';

/**
 * useAuth - Unified Authentication Hook
 *
 * ARCHITECTURAL DECISION:
 * This hook provides a unified interface for Auth0 authentication that works
 * seamlessly with both the real Auth0 SDK and our MockAuth0Provider.
 *
 * PROBLEM SOLVED:
 * - Components were importing useAuth0 directly from @auth0/auth0-react
 * - When using MockAuth0Provider, that context doesn't exist → runtime error
 * - This creates a unified export that delegates to the active provider
 *
 * USAGE:
 * Replace all imports of:
 *   import { useAuth0 } from '@auth0/auth0-react';
 *
 * With:
 *   import { useAuth } from '@/hooks/useAuth';
 *
 * IMPLEMENTATION:
 * The Auth0Provider wrapper component exports a unified hook that works
 * with both real and mock providers. This file re-exports it for convenience.
 */

// Re-export the unified hook from the provider component
export { useAuth0 as useAuth } from '@/components/auth/Auth0Provider';

// Re-export types from Auth0 SDK for convenience
export type {
  User,
  Auth0ContextInterface,
  RedirectLoginOptions,
  LogoutOptions,
} from '@auth0/auth0-react';
