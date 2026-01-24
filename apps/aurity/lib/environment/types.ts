/**
 * Environment Detection Types
 *
 * Enterprise-grade type definitions for runtime environment detection
 * in hybrid web/desktop applications (Tauri + Next.js).
 *
 * @module lib/environment/types
 */

/**
 * Runtime platform where the app is executing.
 *
 * - 'web': Running in a standard browser (Chrome, Firefox, Safari, etc.)
 * - 'tauri': Running inside Tauri desktop shell
 * - 'unknown': SSR or detection not yet complete
 */
export type RuntimePlatform = 'web' | 'tauri' | 'unknown';

/**
 * Build-time deployment target (from env vars).
 *
 * - 'cloud': Built for cloud deployment (app.aurity.io)
 * - 'desktop': Built for desktop distribution (Tauri bundle)
 */
export type DeploymentTarget = 'cloud' | 'desktop';

/**
 * Device form factor based on touch capabilities.
 */
export type DeviceType = 'desktop' | 'mobile' | 'unknown';

/**
 * Complete environment state.
 *
 * This is the "single source of truth" for environment detection.
 * Components should consume this via useEnvironment() hook.
 */
export interface EnvironmentState {
  /** Runtime platform detection (web vs tauri) */
  platform: RuntimePlatform;

  /** Build-time deployment target */
  target: DeploymentTarget;

  /** Device form factor */
  device: DeviceType;

  /** True if running inside Tauri shell */
  isTauri: boolean;

  /** True if running in standard browser */
  isWeb: boolean;

  /** True if this is a desktop device (not touch-primary) */
  isDesktopDevice: boolean;

  /** True if this is a mobile/tablet device */
  isMobileDevice: boolean;

  /** Convenience: Tauri on desktop device */
  isTauriDesktop: boolean;

  /** Convenience: Tauri on mobile device (Android/iOS via Tauri Mobile) */
  isTauriMobile: boolean;

  /** Convenience: Web on desktop browser */
  isWebDesktop: boolean;

  /** Convenience: Web on mobile browser */
  isWebMobile: boolean;

  /** True if detection is complete (false during SSR/hydration) */
  isReady: boolean;

  /** Tauri version if available */
  tauriVersion: string | null;
}

/**
 * Tauri window globals (v1 and v2 compatible).
 */
export interface TauriGlobals {
  __TAURI__?: Record<string, unknown>;
  __TAURI_INTERNALS__?: Record<string, unknown>;
  __AURITY_BACKEND_URL__?: string;
}

/**
 * Extended Window interface with Tauri globals.
 */
declare global {
  interface Window extends TauriGlobals {}
}
