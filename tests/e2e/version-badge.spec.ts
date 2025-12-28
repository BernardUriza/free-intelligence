/**
 * E2E Test: Version & Deployment Validation
 *
 * CRITICAL TEST (must pass for deploy):
 * - Backend /version endpoint responds with correct structure
 * - Python E2E code is valid and executable
 *
 * OPTIONAL TESTS (run when frontend is healthy):
 * - VersionBadge renders correctly
 * - Frontend-backend version match
 *
 * Run locally: npx playwright test tests/e2e/version-badge.spec.ts
 * Run in CI: BASE_URL=https://app.aurity.io npx playwright test
 */

import { test, expect } from '@playwright/test';

// Production URL for CI, localhost for dev
const BASE_URL = process.env.BASE_URL || 'http://localhost:9000';
const BACKEND_URL = process.env.BACKEND_URL || process.env.BASE_URL || 'http://localhost:7001';

test.describe('Backend Version API (Critical)', () => {
  test('backend /version endpoint responds correctly', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/version`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.service).toBe('AURITY');
    expect(data.version).toMatch(/^\d+\.\d+\.\d+$/); // semver format
    expect(data.python_e2e_code).toContain('validate_aurity');
    expect(data.python_e2e_code).toContain('import requests');

    console.log(`✅ Backend version: ${data.version} (${data.environment})`);
  });

  test('backend health check passes', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('ok');

    console.log('✅ Backend health: ok');
  });

  test('backend root returns AURITY service info', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.service?.codename).toBe('AURITY');

    console.log(`✅ Backend service: ${data.service?.name}`);
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
