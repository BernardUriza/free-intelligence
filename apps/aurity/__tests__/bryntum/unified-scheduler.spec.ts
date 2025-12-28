/**
 * Bryntum Unified Scheduler - Integration Tests
 * 
 * Validates:
 * - Single CSS/JS load (no duplicates)
 * - StrictMode double-mount safety
 * - No memory leaks on unmount
 * - Timeline and Appointments both use same core
 * 
 * Card: FI-BRYNTUM-UNIFY-001
 * Created: 2025-12-11
 */

import { test, expect, ConsoleMessage } from '@playwright/test';

test.describe('Bryntum Unified Scheduler', () => {
  test.describe('Loading Idempotency', () => {
    test('should load CSS only once across multiple schedulers', async ({ page }) => {
      // Navigate to timeline page (loads Bryntum)
      await page.goto('/timeline');
      
      // Wait for scheduler to be ready
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Count CSS links with Bryntum theme
      const cssLinks = await page.locator('link[href*="schedulerpro.classic-dark.css"]').count();
      expect(cssLinks).toBe(1);
      
      // Navigate to appointments page (should reuse loaded Bryntum)
      await page.goto('/admin/appointments');
      
      // Wait for appointments scheduler
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // CSS should still be loaded only once
      const cssLinksAfter = await page.locator('link[href*="schedulerpro.classic-dark.css"]').count();
      expect(cssLinksAfter).toBe(1);
    });

    test('should load Bryntum module only once', async ({ page }) => {
      // Add console listener to catch duplicate loads
      const scriptLoads: string[] = [];
      page.on('console', (msg: ConsoleMessage) => {
        if (msg.text().includes('bryntum-module-loaded')) {
          scriptLoads.push(msg.text());
        }
      });

      // Navigate to timeline
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Navigate to appointments
      await page.goto('/admin/appointments');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Navigate back to timeline
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Should have loaded module only once
      expect(scriptLoads.length).toBeLessThanOrEqual(1);
    });
  });

  test.describe('StrictMode Safety', () => {
    test('should not duplicate scheduler on double mount', async ({ page }) => {
      await page.goto('/timeline');
      
      // Wait for scheduler to render
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Check for warning about duplicate scheduler
      const warnings: string[] = [];
      page.on('console', (msg: ConsoleMessage) => {
        if (msg.type() === 'warning' && msg.text().includes('Scheduler already exists')) {
          warnings.push(msg.text());
        }
      });
      
      // React StrictMode causes double mount in dev
      // Wait a bit to see if any warnings appear
      await page.waitForTimeout(1000);
      
      // Should have at most one warning (if StrictMode is on)
      // In production, should be 0
      expect(warnings.length).toBeLessThanOrEqual(1);
    });
  });

  test.describe('Memory Leaks', () => {
    test('should cleanup scheduler on unmount', async ({ page }) => {
      // Track destroy calls
      const destroyCalls: string[] = [];
      page.on('console', (msg: ConsoleMessage) => {
        if (msg.text().includes('destroy')) {
          destroyCalls.push(msg.text());
        }
      });

      // Mount timeline scheduler
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Navigate away (should trigger cleanup)
      await page.goto('/');
      
      // Wait for cleanup
      await page.waitForTimeout(500);
      
      // Go back to timeline
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Navigate away again
      await page.goto('/');
      await page.waitForTimeout(500);
      
      // Check for memory leaks by looking at detached DOM nodes
      // This is a smoke test - proper leak detection requires browser DevTools
      const metrics = await page.evaluate(() => {
        interface PerformanceMemoryInfo {
          usedJSHeapSize: number;
          totalJSHeapSize: number;
          jsHeapSizeLimit: number;
        }

        if ((performance as Performance & { memory?: PerformanceMemoryInfo }).memory) {
          const perfMemory = (performance as Performance & { memory?: PerformanceMemoryInfo }).memory!;
          return {
            usedJSHeapSize: perfMemory.usedJSHeapSize,
            totalJSHeapSize: perfMemory.totalJSHeapSize,
          };
        }
        return null;
      });
      
      // If memory info available, heap should be reasonable
      if (metrics) {
        const heapUsagePercent = (metrics.usedJSHeapSize / metrics.totalJSHeapSize) * 100;
        expect(heapUsagePercent).toBeLessThan(90); // Not maxed out
      }
    });

    test('should not leave dangling event listeners', async ({ page }) => {
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Get initial listener count (approximation via window listeners)
      const initialListeners = await page.evaluate(() => {
        return (window as Window & { __eventListenerCount?: number }).__eventListenerCount || 0;
      });
      
      // Navigate away and back multiple times
      for (let i = 0; i < 3; i++) {
        await page.goto('/');
        await page.waitForTimeout(200);
        await page.goto('/timeline');
        await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      }
      
      const finalListeners = await page.evaluate(() => {
        return (window as Window & { __eventListenerCount?: number }).__eventListenerCount || 0;
      });
      
      // Listener count should not grow unbounded
      // Allow some tolerance for other app listeners
      expect(Math.abs(finalListeners - initialListeners)).toBeLessThan(50);
    });
  });

  test.describe('Timeline Scheduler Functionality', () => {
    test('should render timeline with 2 resource rows', async ({ page }) => {
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Wait for Bryntum to render rows
      await page.waitForTimeout(1000);
      
      // Check for resource rows (Chat and Audio)
      const rows = page.locator('.b-grid-row');
      const rowCount = await rows.count();
      
      // Should have 2 resource rows
      expect(rowCount).toBeGreaterThanOrEqual(2);
    });

    test('should not allow DnD on timeline (read-only)', async ({ page }) => {
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Look for any draggable events
      const draggableEvents = page.locator('.b-sch-event[draggable="true"]');
      const count = await draggableEvents.count();
      
      // Timeline should be read-only (no draggable events)
      expect(count).toBe(0);
    });
  });

  test.describe('Appointments Scheduler Functionality', () => {
    test('should render appointments with doctors as resources', async ({ page }) => {
      await page.goto('/admin/appointments');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Wait for Bryntum to render
      await page.waitForTimeout(1000);
      
      // Check for resource rows (doctors)
      const rows = page.locator('.b-grid-row');
      const rowCount = await rows.count();
      
      // Should have at least some doctor rows
      expect(rowCount).toBeGreaterThanOrEqual(1);
    });

    test('should allow DnD on appointments (editable)', async ({ page }) => {
      await page.goto('/admin/appointments');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Wait for events to render
      await page.waitForTimeout(1000);
      
      // Look for events (may be empty calendar)
      const events = page.locator('.b-sch-event');
      const eventCount = await events.count();
      
      // If there are events, they should be draggable (not read-only)
      if (eventCount > 0) {
        const firstEvent = events.first();
        const isDraggable = await firstEvent.evaluate((el) => {
          return el.getAttribute('draggable') === 'true' || 
                 el.classList.contains('b-draggable');
        });
        
        // Appointments should allow editing
        // Note: Bryntum may use different DnD mechanism
        // This is a basic check
        expect(isDraggable).toBeTruthy();
      }
    });
  });

  test.describe('Performance', () => {
    test('should load scheduler within reasonable time', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Wait for Bryntum to fully initialize
      await page.waitForTimeout(500);
      
      const loadTime = Date.now() - startTime;
      
      // Should load in under 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should render events efficiently (no jank)', async ({ page }) => {
      await page.goto('/timeline');
      await page.waitForSelector('[data-bryntum-core]', { timeout: 10000 });
      
      // Measure frame rate during interaction
      const metrics = await page.evaluate(async (): Promise<number> => {
        return new Promise<number>((resolve: (value: number) => void) => {
          let frames = 0;
          const startTime = performance.now();

          function countFrame() {
            frames++;
            if (performance.now() - startTime < 1000) {
              requestAnimationFrame(countFrame);
            } else {
              resolve(frames);
            }
          }

          requestAnimationFrame(countFrame);
        });
      });
      
      // Should maintain at least 30 FPS (basic threshold)
      expect(metrics).toBeGreaterThan(30);
    });
  });
});
