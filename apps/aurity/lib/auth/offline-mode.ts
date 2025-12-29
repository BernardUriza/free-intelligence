/**
 * Offline Mode Manager for Aurity Desktop
 *
 * Manages controlled offline mode for the desktop application when
 * Auth0 authentication is unavailable.
 *
 * SECURITY CONSIDERATIONS:
 * - Offline mode is DISABLED by default (NEXT_PUBLIC_DESKTOP_OFFLINE=false)
 * - Requires explicit user confirmation to enable
 * - Automatically expires after 24 hours
 * - Limits functionality in offline mode
 * - Logs all offline mode activations (no PHI)
 *
 * USAGE:
 * - Check availability: await checkAuth0Availability()
 * - Enable: await enableOfflineMode('auth_unavailable')
 * - Disable: await disableOfflineMode()
 * - Check status: await isOfflineModeEnabled()
 */

export interface OfflineModeConfig {
  enabled: boolean;
  confirmedAt: number | null; // Unix timestamp (ms)
  reason: 'auth_unavailable' | 'user_requested' | null;
  expiresAt: number | null; // Unix timestamp (ms)
}

const OFFLINE_STORAGE_KEY = 'aurity_offline_mode';
const OFFLINE_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Check if offline mode is currently enabled and valid
 */
export async function isOfflineModeEnabled(): Promise<boolean> {
  if (typeof window === 'undefined') return false;

  try {
    const configStr = localStorage.getItem(OFFLINE_STORAGE_KEY);
    if (!configStr) return false;

    const config: OfflineModeConfig = JSON.parse(configStr);

    // Check if expired
    if (config.expiresAt && Date.now() > config.expiresAt) {
      await disableOfflineMode();
      console.info('[OfflineMode] Session expired, disabled');
      return false;
    }

    return config.enabled;
  } catch {
    return false;
  }
}

/**
 * Get the current offline mode configuration
 */
export async function getOfflineModeConfig(): Promise<OfflineModeConfig | null> {
  if (typeof window === 'undefined') return null;

  try {
    const configStr = localStorage.getItem(OFFLINE_STORAGE_KEY);
    if (!configStr) return null;

    return JSON.parse(configStr);
  } catch {
    return null;
  }
}

/**
 * Enable offline mode with explicit user confirmation
 * @param reason - Why offline mode is being enabled
 */
export async function enableOfflineMode(
  reason: 'auth_unavailable' | 'user_requested'
): Promise<void> {
  const now = Date.now();
  const config: OfflineModeConfig = {
    enabled: true,
    confirmedAt: now,
    reason,
    expiresAt: now + OFFLINE_DURATION_MS,
  };

  localStorage.setItem(OFFLINE_STORAGE_KEY, JSON.stringify(config));

  // Log for audit (no PHI - just the event)
  console.info('[OfflineMode] Enabled', {
    reason,
    expiresAt: new Date(config.expiresAt!).toISOString(),
  });
}

/**
 * Disable offline mode
 */
export async function disableOfflineMode(): Promise<void> {
  localStorage.removeItem(OFFLINE_STORAGE_KEY);
  console.info('[OfflineMode] Disabled');
}

/**
 * Get remaining time until offline mode expires
 * @returns Remaining time in milliseconds, or 0 if not enabled/expired
 */
export async function getOfflineModeRemainingTime(): Promise<number> {
  const config = await getOfflineModeConfig();
  if (!config?.enabled || !config.expiresAt) return 0;

  const remaining = config.expiresAt - Date.now();
  return Math.max(0, remaining);
}

/**
 * Check if Auth0 is reachable
 * Uses the OIDC discovery endpoint which is always available
 */
export async function checkAuth0Availability(): Promise<boolean> {
  try {
    const domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
    if (!domain) {
      console.warn('[OfflineMode] AUTH0_DOMAIN not configured');
      return false;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(
        `https://${domain}/.well-known/openid-configuration`,
        {
          method: 'HEAD',
          signal: controller.signal,
        }
      );
      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      clearTimeout(timeoutId);
      return false;
    }
  } catch {
    return false;
  }
}

/**
 * Get offline mode limitations for display
 */
export function getOfflineModeLimitations(): string[] {
  return [
    'No se sincronizarán datos con la nube',
    'Sin acceso a funciones que requieren autenticación',
    'Historial de chat limitado a sesión actual',
    'El modo expira automáticamente en 24 horas',
  ];
}

/**
 * Format remaining time for display
 * @param ms - Remaining time in milliseconds
 * @returns Formatted string like "23h 45m" or "45m"
 */
export function formatRemainingTime(ms: number): string {
  if (ms <= 0) return 'Expirado';

  const hours = Math.floor(ms / (60 * 60 * 1000));
  const minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}
