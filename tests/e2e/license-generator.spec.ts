/**
 * E2E Test: License Generator (Superadmin)
 *
 * Tests the complete flow of generating a license key from the admin UI.
 * Requires authenticated superadmin user.
 *
 * Run: npx playwright test tests/e2e/license-generator.spec.ts --headed
 */

import { test, expect } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:9000';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:7001';

test.describe('License Generator', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app - Auth0 will redirect to login if not authenticated
    await page.goto(BASE_URL);

    // If we land on Auth0 login, credentials must be provided via env vars
    // For automated CI, use Auth0 test users or mock auth
    if (page.url().includes('auth0.com')) {
      console.log('Auth0 login required - skipping in CI without credentials');
      test.skip();
    }
  });

  test('should show license generator page for superadmin', async ({ page }) => {
    // Navigate to license generator
    await page.goto(`${BASE_URL}/admin/licenses`);

    // Should see the form (if authorized)
    const pageContent = await page.textContent('body');

    if (pageContent?.includes('Acceso No Autorizado')) {
      console.log('User is not superadmin - skipping test');
      test.skip();
    }

    // Check form elements exist
    await expect(page.getByLabel(/Clinic|Clínica/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel(/Auth0 Domain/i)).toBeVisible();
    await expect(page.getByLabel(/Client ID/i)).toBeVisible();
  });

  test('should load clinics in dropdown', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/licenses`);

    // Wait for clinics to load
    await page.waitForResponse(
      (response) => response.url().includes('/api/clinics') && response.status() === 200,
      { timeout: 10000 }
    );

    // Click on clinic selector to see options
    const clinicInput = page.getByPlaceholder(/buscar clínica|search clinic/i);
    if (await clinicInput.isVisible()) {
      await clinicInput.click();
      // Should show at least the demo clinic
      await expect(page.getByText(/Demo AURITY/i)).toBeVisible({ timeout: 5000 });
    }
  });

  test('should generate license with valid data', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/licenses`);

    // Fill form
    const clinicInput = page.getByPlaceholder(/buscar clínica|search clinic/i);
    if (await clinicInput.isVisible()) {
      await clinicInput.fill('Demo');
      await page.getByText(/Demo AURITY/i).click();
    }

    // Auth0 fields should be pre-filled, but verify
    const auth0Domain = page.getByLabel(/Auth0 Domain/i);
    await expect(auth0Domain).toHaveValue(/\.auth0\.com/);

    // Submit form
    const submitButton = page.getByRole('button', { name: /generar|generate/i });
    await submitButton.click();

    // Wait for response
    const response = await page.waitForResponse(
      (response) =>
        response.url().includes('/api/admin/licenses/generate') &&
        (response.status() === 200 || response.status() === 201),
      { timeout: 15000 }
    );

    expect(response.ok()).toBe(true);

    // License key should be displayed
    await expect(page.getByText(/AURITY-/i)).toBeVisible({ timeout: 5000 });
  });
});

// API-level tests (bypass UI, use captured token)
test.describe('License API', () => {
  const API_TOKEN = process.env.AUTH0_TEST_TOKEN;

  test.skip(!API_TOKEN, 'Skipping API tests - AUTH0_TEST_TOKEN not set');

  test('GET /api/admin/licenses/features returns feature list', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/admin/licenses/features`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.features).toBeDefined();
    expect(Array.isArray(data.features)).toBe(true);
  });

  test('POST /api/admin/licenses/generate creates license', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/api/admin/licenses/generate`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        'Content-Type': 'application/json',
      },
      data: {
        clinic_id: 'test-e2e-clinic',
        clinic_name: 'E2E Test Clinic',
        auth0_domain: 'dev-test.us.auth0.com',
        auth0_client_id: 'test-client-id',
        auth0_audience: 'https://app.aurity.io',
        features: ['soap', 'timeline'],
        expires_days: 30,
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.license_key).toBeDefined();
    expect(data.license_key).toMatch(/^AURITY-/);
    expect(data.clinic_id).toBe('test-e2e-clinic');
  });
});
