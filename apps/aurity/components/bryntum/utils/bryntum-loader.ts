/**
 * Bryntum Loader - Singleton Module Loader
 * 
 * Eliminates duplicate CSS/JS loads, handles CSP nonces, and ensures
 * StrictMode double-mount safety.
 * 
 * Architecture:
 * - Single promise per resource (keyed by href/module path)
 * - No window globals or custom events
 * - Idempotent: multiple calls return the same promise
 * - CSP-compliant: optional nonce support
 * 
 * Card: FI-BRYNTUM-UNIFY-001
 * Created: 2025-12-11
 */

// ============================================================================
// Types
// ============================================================================

interface LoadBryntumOptions {
  cssHref: string;
  umdPath: string;
  nonce?: string;
  // When true, will auto-correct CSS href to match JS version if mismatch
  strictVersionMatch?: boolean;
  // Optional additional CSS files to load after the main theme (e.g., overrides)
  extraCss?: string[];
}

interface LoadedResource {
  promise: Promise<void>;
  loaded: boolean;
}

// ============================================================================
// State (module-level singleton)
// ============================================================================

const loadedResources = new Map<string, LoadedResource>();
let bryntumModule: any = null;

// ============================================================================
// CSS Loader
// ============================================================================

/**
 * Load CSS stylesheet with idempotent guard
 * Returns immediately if already loaded/loading
 */
function loadCSS(href: string, nonce?: string): Promise<void> {
  const existing = loadedResources.get(href);
  if (existing) {
    return existing.promise;
  }

  // Check if already in DOM
  const existingLink = document.querySelector(`link[href="${href}"]`);
  if (existingLink) {
    const resolved = Promise.resolve();
    loadedResources.set(href, { promise: resolved, loaded: true });
    return resolved;
  }

  // Create new promise for this resource
  const promise = new Promise<void>((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    
    if (nonce) {
      link.setAttribute('nonce', nonce);
    }

    link.onload = () => {
      const resource = loadedResources.get(href);
      if (resource) {
        resource.loaded = true;
      }
      resolve();
    };

    link.onerror = () => {
      loadedResources.delete(href);
      reject(new Error(`Failed to load CSS: ${href}`));
    };

    document.head.appendChild(link);
  });

  loadedResources.set(href, { promise, loaded: false });
  return promise;
}

// ============================================================================
// Module Loader
// ============================================================================

/**
 * Load Bryntum UMD/ESM module dynamically
 * Uses dynamic import with webpackIgnore for Next.js compatibility
 * 
 * Uses inline script + window global (Bryntum requires UMD loading in Next.js).
 */
function loadModule(umdPath: string, nonce?: string): Promise<any> {
  const existing = loadedResources.get(umdPath);
  if (existing) {
    return existing.promise.then(() => bryntumModule);
  }

  // Check if module already loaded
  if (bryntumModule) {
    const resolved = Promise.resolve();
    loadedResources.set(umdPath, { promise: resolved, loaded: true });
    return resolved.then(() => bryntumModule);
  }

  // Load module via inline script (temp solution for UMD)
  const promise = new Promise<any>((resolve, reject) => {
    // Check if already loading via existing script
    const existingScript = document.querySelector(`script[data-bryntum-module="${umdPath}"]`);
    if (existingScript) {
      // Wait for existing script to complete
      const handleLoaded = () => {
        window.removeEventListener('bryntum-module-loaded', handleLoaded);
        if (bryntumModule) {
          resolve(bryntumModule);
        } else {
          reject(new Error('Bryntum module loaded but not accessible'));
        }
      };
      window.addEventListener('bryntum-module-loaded', handleLoaded);
      return;
    }

    const script = document.createElement('script');
    script.type = 'module';
    script.setAttribute('data-bryntum-module', umdPath);
    
    if (nonce) {
      script.setAttribute('nonce', nonce);
    }

    // Dynamic import via inline module
    script.textContent = `
      import { SchedulerPro } from "${umdPath}";
      window.__BryntumSchedulerPro = SchedulerPro;
      window.dispatchEvent(new CustomEvent("bryntum-module-loaded"));
    `;

    const handleLoaded = () => {
      window.removeEventListener('bryntum-module-loaded', handleLoaded);
      
      // Store module reference
      bryntumModule = (window as any).__BryntumSchedulerPro;
      
      if (bryntumModule) {
        const resource = loadedResources.get(umdPath);
        if (resource) {
          resource.loaded = true;
        }
        resolve(bryntumModule);
      } else {
        loadedResources.delete(umdPath);
        reject(new Error('Bryntum SchedulerPro failed to load'));
      }
    };

    window.addEventListener('bryntum-module-loaded', handleLoaded);
    document.head.appendChild(script);

    // Timeout fallback
    setTimeout(() => {
      window.removeEventListener('bryntum-module-loaded', handleLoaded);
      loadedResources.delete(umdPath);
      reject(new Error(`Bryntum module load timeout: ${umdPath}`));
    }, 15000);
  });

  loadedResources.set(umdPath, { promise: promise.then(() => {}), loaded: false });
  return promise;
}

// ============================================================================
// Public API
// ============================================================================

// ----------------------------------------------------------------------------
// Version helpers
// ----------------------------------------------------------------------------

function extractVersionFromPath(path: string): string | null {
  // Try to find x.y.z(-suffix) patterns
  const match = path.match(/\b(\d+\.\d+\.\d+(?:[-a-z0-9.]+)?)\b/i);
  return match ? match[1] : null;
}

function versionsMismatch(cssHref: string, umdPath: string): { css?: string; js?: string; mismatch: boolean } {
  const cssVer = extractVersionFromPath(cssHref);
  const jsVer = extractVersionFromPath(umdPath);
  return { css: cssVer ?? undefined, js: jsVer ?? undefined, mismatch: !!(cssVer && jsVer && cssVer !== jsVer) };
}

function tryAlignCssVersion(cssHref: string, umdPath: string): string {
  const jsVer = extractVersionFromPath(umdPath);
  if (!jsVer) return cssHref;

  // Replace any detected version segment in cssHref with jsVer
  const replaced = cssHref.replace(/\b\d+\.\d+\.\d+(?:[-a-z0-9.]+)?\b/i, jsVer);
  if (replaced !== cssHref) return replaced;

  // If no explicit version in cssHref, attempt common Bryntum path patterns
  // e.g., /css/bryntum/6.0.0/schedulerpro.classic.css
  const parts = cssHref.split('/');
  const idx = parts.findIndex(p => p.toLowerCase() === 'bryntum');
  if (idx >= 0) {
    const insertIdx = idx + 1;
    // Insert jsVer if not present
    if (parts[insertIdx] !== jsVer) {
      parts.splice(insertIdx, 0, jsVer);
      return parts.join('/');
    }
  }
  return cssHref;
}

/**
 * Load Bryntum SchedulerPro (CSS + JS module)
 * 
 * Idempotent: Safe to call multiple times, returns same promise.
 * StrictMode-safe: Double mounts won't cause duplicate loads.
 * 
 * @param options - CSS href, UMD path, optional CSP nonce
 * @returns Promise that resolves when both CSS and module are loaded
 * 
 * @example
 * ```ts
 * await loadBryntumOnce({
 *   cssHref: '/css/bryntum/schedulerpro.classic-dark.css',
 *   umdPath: '/js/bryntum/schedulerpro.wc.module.js',
 *   nonce: window.__CSP_NONCE__
 * });
 * 
 * const scheduler = new window.__BryntumSchedulerPro({ ... });
 * ```
 */
export async function loadBryntumOnce(options: LoadBryntumOptions): Promise<void> {
  const { nonce, strictVersionMatch } = options;
  let { cssHref, umdPath } = options;
  const extraCss = options.extraCss ?? [];

  // Detect version mismatch and optionally align CSS
  const vm = versionsMismatch(cssHref, umdPath);
  if (vm.mismatch) {
    // eslint-disable-next-line no-console
    console.warn('[BryntumLoader] CSS/JS version mismatch detected', { cssVersion: vm.css, jsVersion: vm.js, cssHref, umdPath });
    if (strictVersionMatch) {
      const alignedCss = tryAlignCssVersion(cssHref, umdPath);
      if (alignedCss !== cssHref) {
        // eslint-disable-next-line no-console
        console.info('[BryntumLoader] Aligning CSS href to JS version', { from: cssHref, to: alignedCss });
        cssHref = alignedCss;
      }
    }
  }
  
  // Load main CSS and module in parallel
  await Promise.all([
    loadCSS(cssHref, nonce),
    loadModule(umdPath, nonce)
  ]);

  // Load any override CSS files sequentially after main theme
  for (const href of extraCss) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await loadCSS(href, nonce);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('[BryntumLoader] Failed to load extra CSS', { href, error: e });
    }
  }
}

/**
 * Check if Bryntum is already loaded
 * Useful for conditional rendering or preload checks
 */
export function isLoaded(): boolean {
  return bryntumModule !== null;
}

/**
 * Get the loaded Bryntum module
 * Returns null if not yet loaded
 */
export function getBryntumModule(): any {
  return bryntumModule;
}

/**
 * Reset loader state (for testing only)
 * @internal
 */
export function _resetLoader(): void {
  loadedResources.clear();
  bryntumModule = null;
}
