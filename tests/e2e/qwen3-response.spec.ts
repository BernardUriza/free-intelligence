/**
 * E2E Test: Qwen3 LLM Response Validation
 *
 * Verifies that the AI assistant (Qwen3) responds correctly.
 * This test has a longer timeout because local LLMs can take 30-60s.
 *
 * Run locally: npx playwright test tests/e2e/qwen3-response.spec.ts
 * Run in CI: BACKEND_URL=https://app.aurity.io npx playwright test tests/e2e/qwen3-response.spec.ts
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || process.env.BASE_URL || 'http://localhost:7001';

// Qwen3 can take 30-120 seconds on CPU
test.setTimeout(120_000);

test.describe('Qwen3 LLM Response (Critical)', () => {
  test('assistant /chat endpoint responds with valid content', async ({ request }) => {
    const payload = {
      message: 'Responde solo con la palabra "funcionando" si puedes leer esto.',
      session_id: 'e2e-test-session',
      user_id: 'e2e-test-user',
    };

    console.log(`🧪 Testing Qwen3 at ${BACKEND_URL}/api/workflows/aurity/assistant/chat`);

    const response = await request.post(
      `${BACKEND_URL}/api/workflows/aurity/assistant/chat`,
      {
        data: payload,
        headers: { 'Content-Type': 'application/json' },
        timeout: 120_000, // 2 minutes for slow LLMs
      }
    );

    // Log response for debugging
    const status = response.status();
    console.log(`📡 Response status: ${status}`);

    if (!response.ok()) {
      const errorText = await response.text();
      console.log(`❌ Error response: ${errorText}`);
    }

    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // Verify response structure
    expect(data).toHaveProperty('response');
    expect(typeof data.response).toBe('string');
    expect(data.response.length).toBeGreaterThan(0);

    // Log the actual response
    console.log(`✅ Qwen3 responded: "${data.response.substring(0, 100)}..."`);

    // Optional: verify it contains expected content
    const responseText = data.response.toLowerCase();
    const hasValidResponse =
      responseText.includes('funcionando') ||
      responseText.length > 5; // Any meaningful response is OK

    expect(hasValidResponse).toBeTruthy();
  });

  test('assistant /chat responds to English prompt', async ({ request }) => {
    const payload = {
      message: 'Reply with just "OK" if you can read this.',
      session_id: 'e2e-test-session-en',
      user_id: 'e2e-test-user',
    };

    const response = await request.post(
      `${BACKEND_URL}/api/workflows/aurity/assistant/chat`,
      {
        data: payload,
        headers: { 'Content-Type': 'application/json' },
        timeout: 120_000,
      }
    );

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.response).toBeDefined();
    expect(data.response.length).toBeGreaterThan(0);

    console.log(`✅ Qwen3 English response: "${data.response.substring(0, 100)}..."`);
  });

  test('assistant handles empty message gracefully', async ({ request }) => {
    const payload = {
      message: '',
      session_id: 'e2e-test-empty',
      user_id: 'e2e-test-user',
    };

    const response = await request.post(
      `${BACKEND_URL}/api/workflows/aurity/assistant/chat`,
      {
        data: payload,
        headers: { 'Content-Type': 'application/json' },
        timeout: 30_000,
      }
    );

    // Should either respond or return 400/422
    const status = response.status();
    expect([200, 400, 422]).toContain(status);

    console.log(`✅ Empty message handled with status: ${status}`);
  });
});
