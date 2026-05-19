/**
 * Deployment Configuration
 *
 * Backend URLs and deployment-specific settings.
 * For environment detection (web vs desktop), use @/lib/environment instead.
 *
 * @module lib/config/deployment
 * @see lib/environment for runtime detection
 */

import {
  detectTauri,
  isBrowser,
  getDeploymentTarget,
  // Re-export for backward compatibility
  isDesktop,
  isCloud,
} from '@/lib/environment';
import { createLogger } from '@/lib/internal/logger';

// Re-export types and functions for backward compatibility
export type { DeploymentTarget } from '@/lib/environment';
export { isDesktop, isCloud, getDeploymentTarget as getTarget };

/**
 * Default backend URLs for each deployment target
 *
 * Port allocation:
 *   - Cloud:         7001-7050 (backend), 9000 (frontend)
 *   - Desktop dev:   7051 (backend), 9050 (frontend)
 *   - Desktop prod:  7052+ dynamic (backend), bundled (frontend)
 */
const DEFAULT_BACKEND_URLS = {
  cloud: 'https://app.aurity.io',
  desktop: 'http://localhost:7051',
} as const;

/**
 * Get the backend URL based on deployment target.
 *
 * Priority:
 *   1. Tauri injected URL (window.__AURITY_BACKEND_URL__) - dynamic port
 *   2. Explicit NEXT_PUBLIC_BACKEND_URL (always wins)
 *   3. Empty string for same-origin relative paths (cloud/web)
 *   4. Default based on Tauri detection (desktop: localhost:7051)
 *
 * @returns Backend API base URL or empty string for same-origin
 */
export function getBackendUrl(): string {
  // In browser, check for Tauri-injected URL first (dynamic port)
  if (isBrowser()) {
    const tauriUrl = (window as Window & { __AURITY_BACKEND_URL__?: string })
      .__AURITY_BACKEND_URL__;
    if (tauriUrl) {
      return tauriUrl;
    }
  }

  // Explicit override always wins
  const explicit = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (explicit) {
    return explicit;
  }

  // Check if actually running in Tauri (not just build target)
  if (isBrowser() && detectTauri()) {
    return DEFAULT_BACKEND_URLS.desktop;
  }

  // Web: prefer same-origin (empty string) to avoid CORS/mixed-content
  // This works because frontend and backend share domain in cloud
  return '';
}

/**
 * Get the full backend URL (always absolute, for cases where relative won't work).
 *
 * @returns Absolute backend URL
 */
export function getAbsoluteBackendUrl(): string {
  // In browser, check for Tauri-injected URL first (dynamic port)
  if (isBrowser()) {
    const tauriUrl = (window as Window & { __AURITY_BACKEND_URL__?: string })
      .__AURITY_BACKEND_URL__;
    if (tauriUrl) {
      return tauriUrl;
    }
  }

  const explicit = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (explicit) {
    return explicit;
  }

  // Check if actually running in Tauri
  if (isBrowser() && detectTauri()) {
    return DEFAULT_BACKEND_URLS.desktop;
  }

  return DEFAULT_BACKEND_URLS.cloud;
}

/**
 * Check if the app should show desktop-specific UI elements.
 *
 * @deprecated Use useTauriDesktop() hook from @/lib/environment instead.
 */
export function shouldShowDesktopUI(): boolean {
  return isDesktop();
}

/**
 * Get the default Ollama host for frontend display/configuration.
 */
export function getDefaultOllamaHost(): string {
  return 'http://localhost:11434';
}

/**
 * Get the backend port number (for display purposes).
 */
export function getBackendPort(): number | null {
  const url = getBackendUrl();
  if (!url) return null;

  try {
    const parsed = new URL(url);
    return parseInt(parsed.port) || (parsed.protocol === 'https:' ? 443 : 80);
  } catch {
    const match = url.match(/:(\d+)/);
    return match ? parseInt(match[1]) : null;
  }
}

/**
 * Log deployment configuration (for debugging).
 */
export function logDeploymentConfig(): void {
  if (!isBrowser()) return;

  const isDev = process.env.NODE_ENV === 'development';
  if (!isDev) return;

  const deployLog = createLogger('Deployment');
  deployLog.debug('Config', {
    target: getDeploymentTarget(),
    isTauri: detectTauri(),
    backendUrl: getBackendUrl(),
    absoluteBackendUrl: getAbsoluteBackendUrl(),
    isCloud: isCloud(),
    isDesktop: isDesktop(),
  });
}
