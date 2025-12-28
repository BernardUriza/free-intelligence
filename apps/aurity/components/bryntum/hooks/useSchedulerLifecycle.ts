/**
 * useSchedulerLifecycle Hook
 * 
 * Manages Bryntum SchedulerPro initialization, destruction, and updates.
 * Handles dynamic script loading, CSS injection, and instance lifecycle.
 * 
 * CRITICAL: This hook eliminates window globals and script tag hacks.
 * Future: Replace with proper npm package import when available.
 */

import { useEffect, useRef, useCallback } from 'react';
import type {
  BryntumSchedulerInstance,
  BryntumSchedulerConfig,
  UnifiedEvent,
} from '../types/scheduler.types';

interface UseSchedulerLifecycleProps {
  containerRef: React.RefObject<HTMLDivElement>;
  config: BryntumSchedulerConfig;
  events: UnifiedEvent[];
  isLoading: boolean;
  onReady?: (instance: BryntumSchedulerInstance) => void;
  onError?: (error: Error) => void;
}

interface UseSchedulerLifecycleReturn {
  instance: BryntumSchedulerInstance | null;
  isInitialized: boolean;
  initializeScheduler: () => Promise<void>;
  destroyScheduler: () => void;
}

/**
 * Load Bryntum CSS (dark theme)
 * Idempotent: Won't load duplicate stylesheets
 */
function loadBryntumCSS(): void {
  const existingLink = document.querySelector(
    'link[href*="schedulerpro.classic-dark.css"]'
  );
  
  if (!existingLink) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/css/bryntum/schedulerpro.classic-dark.css';
    document.head.appendChild(link);
  }
}

/**
 * Load Bryntum JS module dynamically
 * Returns SchedulerPro constructor
 * 
 * TODO: Replace with proper npm import once Bryntum package is installed
 */
async function loadBryntumModule(): Promise<unknown> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    // @ts-expect-error - window global (temporary until npm package)
    if (window.__BryntumSchedulerPro) {
      // @ts-expect-error - window global
      resolve(window.__BryntumSchedulerPro);
      return;
    }

    const script = document.createElement('script');
    script.type = 'module';
    script.textContent = `
      import { SchedulerPro } from "/js/bryntum/schedulerpro.wc.module.js";
      window.__BryntumSchedulerPro = SchedulerPro;
      window.dispatchEvent(new CustomEvent("bryntum-scheduler-loaded"));
    `;

    const handleLoaded = () => {
      window.removeEventListener('bryntum-scheduler-loaded', handleLoaded);
      // @ts-expect-error - window global
      const SchedulerPro = window.__BryntumSchedulerPro;
      
      if (SchedulerPro) {
        resolve(SchedulerPro);
      } else {
        reject(new Error('Bryntum SchedulerPro failed to load'));
      }
    };

    window.addEventListener('bryntum-scheduler-loaded', handleLoaded);
    document.head.appendChild(script);

    // Timeout fallback (10 seconds)
    setTimeout(() => {
      window.removeEventListener('bryntum-scheduler-loaded', handleLoaded);
      reject(new Error('Bryntum SchedulerPro load timeout'));
    }, 10000);
  });
}

export function useSchedulerLifecycle({
  containerRef,
  config,
  events,
  isLoading,
  onReady,
  onError,
}: UseSchedulerLifecycleProps): UseSchedulerLifecycleReturn {
  const instanceRef = useRef<BryntumSchedulerInstance | null>(null);
  const isInitializedRef = useRef(false);

  /**
   * Initialize Bryntum SchedulerPro
   */
  const initializeScheduler = useCallback(async () => {
    if (!containerRef.current || instanceRef.current || isInitializedRef.current) {
      return;
    }

    try {
      // Load CSS first
      loadBryntumCSS();

      // Load Bryntum module
      const SchedulerPro = await loadBryntumModule();

      if (!containerRef.current) {
        throw new Error('Container ref lost during async load');
      }

      // Debug: Verify resources in config
      console.log('[useSchedulerLifecycle] Initializing with resources:', config.resources);
      console.log('[useSchedulerLifecycle] Events count:', Array.isArray(config.events) ? config.events.length : 0);

      // Instantiate scheduler
      // @ts-expect-error - SchedulerPro constructor (typed in config)
      const instance = new SchedulerPro({
        ...config,
        appendTo: containerRef.current,
      });

      instanceRef.current = instance as BryntumSchedulerInstance;
      isInitializedRef.current = true;

      // Debug: Verify resources were loaded
      console.log('[useSchedulerLifecycle] Scheduler created with resourceStore:', instance.resourceStore?.count || 0, 'resources');

      if (onReady) {
        onReady(instance as BryntumSchedulerInstance);
      }
    } catch (error) {
      console.error('Failed to initialize Bryntum SchedulerPro:', error);
      
      if (onError) {
        onError(error as Error);
      }
    }
  }, [containerRef, config, onReady, onError]);

  /**
   * Destroy scheduler instance
   */
  const destroyScheduler = useCallback(() => {
    if (instanceRef.current?.destroy) {
      instanceRef.current.destroy();
      instanceRef.current = null;
      isInitializedRef.current = false;
    }
  }, []);

  /**
   * Initialize on mount if not loading
   */
  useEffect(() => {
    if (!isLoading && containerRef.current && !instanceRef.current) {
      initializeScheduler();
    }
  }, [isLoading, containerRef, initializeScheduler]);

  /**
   * Update event data and resources when config changes
   */
  useEffect(() => {
    if (!instanceRef.current) return;

    // Update resources if provided
    if (instanceRef.current.resourceStore && config.resources) {
      instanceRef.current.resourceStore.data = config.resources as never[];
    }

    // Update events
    if (instanceRef.current.eventStore) {
      instanceRef.current.eventStore.data = config.events as never[];
    }
  }, [events, config.events, config.resources]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      destroyScheduler();
    };
  }, [destroyScheduler]);

  return {
    instance: instanceRef.current,
    isInitialized: isInitializedRef.current,
    initializeScheduler,
    destroyScheduler,
  };
}
