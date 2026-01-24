/**
 * Environment Detection Logic
 *
 * SSR-safe, Tauri v1/v2 compatible detection functions.
 * These are pure functions that can be called anywhere.
 *
 * Based on Tauri best practices:
 * @see https://github.com/tauri-apps/tauri/discussions/6119
 *
 * @module lib/environment/detection
 */

import type {
  RuntimePlatform,
  DeploymentTarget,
  DeviceType,
  EnvironmentState,
} from './types';

/**
 * Check if code is running in browser (not SSR).
 */
export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

/**
 * Detect if running inside Tauri shell.
 *
 * Checks both Tauri v1 (`__TAURI__`) and v2 (`__TAURI_INTERNALS__`).
 * This is the AUTHORITATIVE check for Tauri runtime.
 */
export function detectTauri(): boolean {
  if (!isBrowser()) return false;

  // Tauri v2 uses __TAURI_INTERNALS__
  if ('__TAURI_INTERNALS__' in window) return true;

  // Tauri v1 uses __TAURI__
  if ('__TAURI__' in window) return true;

  return false;
}

/**
 * Get the runtime platform.
 */
export function detectPlatform(): RuntimePlatform {
  if (!isBrowser()) return 'unknown';
  return detectTauri() ? 'tauri' : 'web';
}

/**
 * Get the build-time deployment target from env var.
 *
 * IMPORTANT: This returns what the app was BUILT for, not where it's running.
 * For runtime detection, use detectTauri() or detectPlatform().
 */
export function getDeploymentTarget(): DeploymentTarget {
  const target = process.env.NEXT_PUBLIC_DEPLOYMENT_TARGET;
  return target === 'cloud' ? 'cloud' : 'desktop';
}

/**
 * Detect device type based on touch capabilities.
 *
 * Uses navigator.maxTouchPoints which is more reliable than user agent parsing.
 */
export function detectDevice(): DeviceType {
  if (!isBrowser()) return 'unknown';

  // maxTouchPoints > 0 indicates touch-capable device
  // However, some laptops have touchscreens, so we also check screen width
  const hasTouch = navigator.maxTouchPoints > 0;
  const isNarrowScreen = window.innerWidth < 768;

  // Mobile: has touch AND narrow screen (phones/small tablets)
  // Desktop: no touch OR wide screen with touch (laptop with touchscreen)
  if (hasTouch && isNarrowScreen) {
    return 'mobile';
  }

  return 'desktop';
}

/**
 * Get Tauri version if available.
 */
export async function getTauriVersion(): Promise<string | null> {
  if (!detectTauri()) return null;

  try {
    // Dynamic import to avoid bundling Tauri in web builds
    const { getVersion } = await import('@tauri-apps/api/app');
    return await getVersion();
  } catch {
    return null;
  }
}

/**
 * Build complete environment state.
 *
 * This is the main function that creates the full EnvironmentState object.
 * Call this once and pass the result to the EnvironmentProvider.
 */
export function detectEnvironment(): EnvironmentState {
  const platform = detectPlatform();
  const target = getDeploymentTarget();
  const device = detectDevice();

  const isTauri = platform === 'tauri';
  const isWeb = platform === 'web';
  const isDesktopDevice = device === 'desktop';
  const isMobileDevice = device === 'mobile';
  const isReady = isBrowser();

  return {
    platform,
    target,
    device,
    isTauri,
    isWeb,
    isDesktopDevice,
    isMobileDevice,
    isTauriDesktop: isTauri && isDesktopDevice,
    isTauriMobile: isTauri && isMobileDevice,
    isWebDesktop: isWeb && isDesktopDevice,
    isWebMobile: isWeb && isMobileDevice,
    isReady,
    tauriVersion: null, // Async, filled later by provider
  };
}

/**
 * Create initial state for SSR (all unknown/false).
 */
export function createSSRState(): EnvironmentState {
  return {
    platform: 'unknown',
    target: getDeploymentTarget(),
    device: 'unknown',
    isTauri: false,
    isWeb: false,
    isDesktopDevice: false,
    isMobileDevice: false,
    isTauriDesktop: false,
    isTauriMobile: false,
    isWebDesktop: false,
    isWebMobile: false,
    isReady: false,
    tauriVersion: null,
  };
}

// ============================================================================
// LEGACY COMPATIBILITY EXPORTS
// These maintain backward compatibility with existing code
// ============================================================================

/**
 * @deprecated Use detectTauri() for runtime check, or getDeploymentTarget() for build target.
 *
 * This function now correctly checks for ACTUAL Tauri runtime,
 * not just the env var. This fixes the bug where web showed desktop UI.
 */
export function isDesktop(): boolean {
  // CRITICAL FIX: Check for actual Tauri runtime, not just env var
  if (isBrowser()) {
    return detectTauri();
  }
  // During SSR, fall back to build target
  return getDeploymentTarget() === 'desktop';
}

/**
 * @deprecated Use !detectTauri() for runtime check, or getDeploymentTarget() for build target.
 */
export function isCloud(): boolean {
  if (isBrowser()) {
    return !detectTauri();
  }
  return getDeploymentTarget() === 'cloud';
}
