/**
 * Environment Detection Module
 *
 * Enterprise-grade environment detection for hybrid web/desktop apps.
 *
 * ## Quick Start
 *
 * ```tsx
 * // 1. Wrap your app with the provider (layout.tsx)
 * import { EnvironmentProvider } from '@/lib/environment';
 *
 * export default function Layout({ children }) {
 *   return (
 *     <EnvironmentProvider>
 *       {children}
 *     </EnvironmentProvider>
 *   );
 * }
 *
 * // 2. Use hooks in any component
 * import { useEnvironment, useTauriDesktop } from '@/lib/environment';
 *
 * function MyComponent() {
 *   const { isTauri, isWeb, isReady } = useEnvironment();
 *   const isDesktop = useTauriDesktop();
 *
 *   if (!isReady) return <Loading />;
 *   if (isDesktop) return <DesktopView />;
 *   return <WebView />;
 * }
 * ```
 *
 * ## Why This Exists
 *
 * The same Next.js codebase runs in two contexts:
 * 1. **Web**: Browser at app.aurity.io
 * 2. **Desktop**: Tauri shell bundled as native app
 *
 * Previously, environment detection was fragmented:
 * - `deployment.ts` checked env vars (build-time)
 * - Components had inline `'__TAURI__' in window` checks
 * - Default was "desktop" which broke web UI
 *
 * This module provides:
 * - Single source of truth for environment state
 * - SSR-safe detection (no hydration mismatches)
 * - Tauri v1 and v2 compatible
 * - React Context for component access
 * - TypeScript types for all states
 *
 * ## Architecture
 *
 * ```
 * types.ts      → TypeScript interfaces
 * detection.ts  → Pure detection functions (SSR-safe)
 * context.tsx   → React Context + Provider + Hooks
 * index.ts      → Public API (this file)
 * ```
 *
 * @module lib/environment
 */

// Types
export type {
  RuntimePlatform,
  DeploymentTarget,
  DeviceType,
  EnvironmentState,
  TauriGlobals,
} from './types';

// Detection functions (use these outside React)
export {
  isBrowser,
  detectTauri,
  detectPlatform,
  detectDevice,
  getDeploymentTarget,
  detectEnvironment,
  getTauriVersion,
  // Legacy compatibility (deprecated but still work)
  isDesktop,
  isCloud,
} from './detection';

// React Context + Hooks (use these in components)
export {
  EnvironmentProvider,
  useEnvironment,
  useTauriDesktop,
  useWebBrowser,
  useStandaloneEnvironment,
} from './context';
