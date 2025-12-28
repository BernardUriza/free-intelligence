/**
 * Deployment target configuration for FI-Cloud vs FI-Edge (Desktop).
 *
 * This module provides a single source of truth for deployment-specific
 * configuration in the frontend. The same codebase runs on both targets,
 * differentiated only by the NEXT_PUBLIC_DEPLOYMENT_TARGET environment variable.
 *
 * Usage:
 *   import { isDesktop, getBackendUrl } from '@/lib/config/deployment';
 *
 *   if (isDesktop()) {
 *     // Desktop-specific logic
 *   }
 *
 * Environment Variables:
 *   NEXT_PUBLIC_DEPLOYMENT_TARGET: "cloud" | "desktop" (default: "desktop")
 *   NEXT_PUBLIC_BACKEND_URL: Override backend endpoint (optional)
 *
 * @module lib/config/deployment
 */

export type DeploymentTarget = 'cloud' | 'desktop';

/**
 * Default backend URLs for each deployment target
 *
 * Port allocation:
 *   - Cloud:         7001-7050 (backend), 9000 (frontend)
 *   - Desktop dev:   7051 (backend), 9050 (frontend)
 *   - Desktop prod:  7052+ dynamic (backend), bundled (frontend)
 */
const DEFAULT_BACKEND_URLS: Record<DeploymentTarget, string> = {
  cloud: 'https://app.aurity.io',
  desktop: 'http://localhost:7051', // Desktop dev uses 7051 to avoid conflict with cloud (7001-7050)
};

/**
 * Get current deployment target from NEXT_PUBLIC_DEPLOYMENT_TARGET env var.
 *
 * @returns 'cloud' for production server, 'desktop' for local app
 */
export function getTarget(): DeploymentTarget {
  const target = process.env.NEXT_PUBLIC_DEPLOYMENT_TARGET;
  if (target === 'cloud') {
    return 'cloud';
  }
  return 'desktop'; // Default to desktop for development
}

/**
 * Check if running in cloud/production mode.
 */
export function isCloud(): boolean {
  return getTarget() === 'cloud';
}

/**
 * Check if running in desktop/local mode.
 */
export function isDesktop(): boolean {
  return getTarget() === 'desktop';
}

/**
 * Get the backend URL based on deployment target.
 *
 * Priority:
 *   1. Tauri injected URL (window.__AURITY_BACKEND_URL__) - dynamic port
 *   2. Explicit NEXT_PUBLIC_BACKEND_URL (always wins)
 *   3. Empty string for same-origin relative paths (cloud production)
 *   4. Default based on target (desktop: localhost:7001)
 *
 * @returns Backend API base URL or empty string for same-origin
 */
export function getBackendUrl(): string {
  // In browser, check for Tauri-injected URL first (dynamic port)
  if (typeof window !== 'undefined') {
    const tauriUrl = (window as Window & { __AURITY_BACKEND_URL__?: string }).__AURITY_BACKEND_URL__;
    if (tauriUrl) {
      return tauriUrl;
    }
  }

  // Explicit override always wins
  const explicit = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (explicit) {
    return explicit;
  }

  // In cloud production, prefer same-origin (empty string) to avoid CORS/mixed-content
  if (isCloud()) {
    return ''; // Same-origin relative paths work when frontend and backend share domain
  }

  // Desktop uses localhost (fallback if Tauri hasn't injected yet)
  return DEFAULT_BACKEND_URLS.desktop;
}

/**
 * Get the full backend URL (always absolute, for cases where relative won't work).
 *
 * @returns Absolute backend URL
 */
export function getAbsoluteBackendUrl(): string {
  // In browser, check for Tauri-injected URL first (dynamic port)
  if (typeof window !== 'undefined') {
    const tauriUrl = (window as Window & { __AURITY_BACKEND_URL__?: string }).__AURITY_BACKEND_URL__;
    if (tauriUrl) {
      return tauriUrl;
    }
  }

  const explicit = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (explicit) {
    return explicit;
  }

  return DEFAULT_BACKEND_URLS[getTarget()];
}

/**
 * Check if the app should show desktop-specific UI elements.
 * Useful for conditionally rendering desktop features like system tray hints.
 */
export function shouldShowDesktopUI(): boolean {
  return isDesktop();
}

/**
 * Get the default Ollama host for frontend display/configuration.
 * The actual Ollama connection is handled by the backend.
 */
export function getDefaultOllamaHost(): string {
  return 'http://localhost:11434';
}

/**
 * Get the backend port number (for display purposes).
 * Returns the dynamic port if available, otherwise the default.
 */
export function getBackendPort(): number | null {
  const url = getBackendUrl();
  if (!url) return null;

  try {
    const parsed = new URL(url);
    return parseInt(parsed.port) || (parsed.protocol === 'https:' ? 443 : 80);
  } catch {
    // Try to extract port from localhost URL
    const match = url.match(/:(\d+)/);
    return match ? parseInt(match[1]) : null;
  }
}

/**
 * Log deployment configuration (for debugging).
 * Only logs in development or when explicitly requested.
 */
export function logDeploymentConfig(): void {
  if (typeof window === 'undefined') return;

  const isDev = process.env.NODE_ENV === 'development';
  if (!isDev) return;

  console.log('[Deployment Config]', {
    target: getTarget(),
    backendUrl: getBackendUrl(),
    absoluteBackendUrl: getAbsoluteBackendUrl(),
    isCloud: isCloud(),
    isDesktop: isDesktop(),
  });
}
