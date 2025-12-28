/**
 * E2E Test: Version Badge Validation
 *
 * Verifies that:
 * 1. Frontend loads successfully
 * 2. VersionBadge component renders
 * 3. Badge fetches and displays correct version from backend
 *
 * Run locally: npx playwright test e2e/version-badge.spec.ts
 * Run in CI: automatically runs post-deploy
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:9000';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:7001';

test.describe('Version Badge E2E', () => {
  test('backend /version endpoint responds correctly', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/version`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.service).toBe('AURITY');
    expect(data.version).toMatch(/^\d+\.\d+\.\d+$/); // semver format
    expect(data.python_e2e_code).toContain('validate_aurity');
  });

  test('frontend loads and version badge appears', async ({ page }) => {
    await page.goto(BASE_URL);

    // Wait for React hydration
    await page.waitForLoadState('networkidle');

    // Find the version badge (with timeout for client-side render)
    const badge = page.locator('[data-testid="version-badge"]');
    await expect(badge).toBeVisible({ timeout: 10000 });

    // Check data attributes
    const version = await badge.getAttribute('data-version');
    expect(version).not.toBe('loading');
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);

    console.log(`✅ Version badge found: v${version}`);
  });

  test('version badge shows correct environment', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const badge = page.locator('[data-testid="version-badge"]');
    await expect(badge).toBeVisible({ timeout: 10000 });

    const env = await badge.getAttribute('data-environment');
    expect(['development', 'production']).toContain(env);

    console.log(`✅ Environment: ${env}`);
  });

  test('version badge is clickable and expands', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const badge = page.locator('[data-testid="version-badge"]');
    await expect(badge).toBeVisible({ timeout: 10000 });

    // Click to expand
    await badge.click();

    // Check for expanded content
    const serviceLabel = page.locator('text=Service:');
    await expect(serviceLabel).toBeVisible({ timeout: 2000 });

    console.log('✅ Badge expands on click');
  });

  test('frontend-backend version match', async ({ page, request }) => {
    // Get backend version
    const backendResponse = await request.get(`${BACKEND_URL}/version`);
    const backendData = await backendResponse.json();
    const backendVersion = backendData.version;

    // Get frontend badge version
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const badge = page.locator('[data-testid="version-badge"]');
    await expect(badge).toBeVisible({ timeout: 10000 });

    const frontendVersion = await badge.getAttribute('data-version');

    // They should match (frontend fetches from backend)
    expect(frontendVersion).toBe(backendVersion);

    console.log(`✅ Versions match: frontend=${frontendVersion}, backend=${backendVersion}`);
  });
});
