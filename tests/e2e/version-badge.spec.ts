/**
 * E2E Test: Version & Deployment Validation
 *
 * CRITICAL TESTS (must pass for deploy):
 * - Backend /api/version endpoint responds with correct structure
 * - Backend /api/health returns ok
 * - Backend /api/ returns AURITY service info
 *
 * OPTIONAL TESTS (skipped in CI):
 * - VersionBadge renders correctly (needs RUN_FRONTEND_TESTS=true)
 *
 * Run locally: npx playwright test tests/e2e/version-badge.spec.ts
 * Run in CI: BACKEND_URL=https://app.aurity.io npx playwright test
 */

import { test, expect } from '@playwright/test';

// Production URL for CI, localhost for dev
const BASE_URL = process.env.BASE_URL || 'http://localhost:9000';
const BACKEND_URL = process.env.BACKEND_URL || process.env.BASE_URL || 'http://localhost:7001';

test.describe('Backend Version API (Critical)', () => {
  test('backend /api/version endpoint responds correctly', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/version`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.service).toBe('AURITY');
    expect(data.version).toMatch(/^\d+\.\d+\.\d+$/); // semver format
    expect(data.environment).toBeDefined();

    console.log(`✅ Backend version: ${data.version} (${data.environment})`);
  });

  test('backend /api/health check passes', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('ok');

    console.log('✅ Backend health: ok');
  });

  test('backend /api/ returns AURITY service info', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    // Backend returns flat structure: {service: "AURITY", status: "operational"}
    expect(data.service).toBe('AURITY');
    expect(data.status).toBe('operational');

    console.log(`✅ Backend service: ${data.service} (${data.status})`);
  });
});

// Frontend tests - skip if frontend has errors (non-blocking for deploy)
test.describe('Frontend Version Badge (Optional)', () => {
  test.skip(({ browserName }) => !process.env.RUN_FRONTEND_TESTS, 'Skipped unless RUN_FRONTEND_TESTS=true');

  test('frontend loads and version badge appears', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const badge = page.locator('[data-testid="version-badge"]');
    await expect(badge).toBeVisible({ timeout: 10000 });

    const version = await badge.getAttribute('data-version');
    expect(version).not.toBe('loading');
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);

    console.log(`✅ Version badge found: v${version}`);
  });
});
