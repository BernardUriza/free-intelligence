'use client';

/**
 * Environment Context Provider
 *
 * React Context that provides environment state to all components.
 * This is the recommended way to access environment info in components.
 *
 * Usage:
 *   // In layout.tsx
 *   <EnvironmentProvider>
 *     {children}
 *   </EnvironmentProvider>
 *
 *   // In any component
 *   const { isTauri, isWeb } = useEnvironment();
 *
 * @module lib/environment/context
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import type { EnvironmentState } from './types';
import {
  detectEnvironment,
  createSSRState,
  getTauriVersion,
  isBrowser,
} from './detection';

// Create context with SSR-safe initial state
const EnvironmentContext = createContext<EnvironmentState>(createSSRState());

// Display name for React DevTools
EnvironmentContext.displayName = 'EnvironmentContext';

interface EnvironmentProviderProps {
  children: ReactNode;
}

/**
 * Environment Provider Component
 *
 * Wrap your app with this to enable useEnvironment() in all components.
 * Place it near the root of your component tree, but inside any providers
 * it might depend on.
 */
export function EnvironmentProvider({ children }: EnvironmentProviderProps) {
  // Start with SSR state, then hydrate on client
  const [state, setState] = useState<EnvironmentState>(createSSRState);

  useEffect(() => {
    // Detect environment on mount (client-side only)
    const env = detectEnvironment();
    setState(env);

    // Async: fetch Tauri version if available
    if (env.isTauri) {
      getTauriVersion().then((version) => {
        if (version) {
          setState((prev) => ({ ...prev, tauriVersion: version }));
        }
      });
    }

    // Log in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[Environment]', {
        platform: env.platform,
        target: env.target,
        device: env.device,
        isTauri: env.isTauri,
        isReady: true,
      });
    }
  }, []);

  // Memoize to prevent unnecessary re-renders
  const value = useMemo(() => state, [state]);

  return (
    <EnvironmentContext.Provider value={value}>
      {children}
    </EnvironmentContext.Provider>
  );
}

/**
 * Hook to access environment state.
 *
 * @example
 * function MyComponent() {
 *   const { isTauri, isWeb, isReady } = useEnvironment();
 *
 *   if (!isReady) return <Loading />;
 *
 *   if (isTauri) {
 *     return <DesktopView />;
 *   }
 *
 *   return <WebView />;
 * }
 */
export function useEnvironment(): EnvironmentState {
  const context = useContext(EnvironmentContext);

  if (context === undefined) {
    throw new Error('useEnvironment must be used within an EnvironmentProvider');
  }

  return context;
}

/**
 * Hook that returns true only when running in Tauri desktop.
 *
 * This is the CORRECT way to check for desktop mode.
 * It waits for hydration to complete before returning true.
 *
 * @example
 * function DesktopOnlyFeature() {
 *   const isDesktop = useTauriDesktop();
 *
 *   if (!isDesktop) return null;
 *
 *   return <DesktopFeature />;
 * }
 */
export function useTauriDesktop(): boolean {
  const { isTauriDesktop, isReady } = useEnvironment();
  return isReady && isTauriDesktop;
}

/**
 * Hook that returns true only when running in web browser.
 *
 * @example
 * function WebOnlyFeature() {
 *   const isWeb = useWebBrowser();
 *
 *   if (!isWeb) return null;
 *
 *   return <DownloadAppBanner />;
 * }
 */
export function useWebBrowser(): boolean {
  const { isWeb, isReady } = useEnvironment();
  return isReady && isWeb;
}

/**
 * Standalone hook for components outside EnvironmentProvider.
 *
 * Use this sparingly - prefer useEnvironment() when possible.
 * This is useful for components that need to check environment
 * before the provider is mounted (e.g., in layout boundary).
 */
export function useStandaloneEnvironment(): EnvironmentState {
  const [state, setState] = useState<EnvironmentState>(createSSRState);

  useEffect(() => {
    setState(detectEnvironment());
  }, []);

  return state;
}
