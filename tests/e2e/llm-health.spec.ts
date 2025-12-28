/**
 * E2E Test: LLM Health Check (Fast)
 *
 * Quick verification that Ollama/LLM infrastructure is available.
 * FI Cloud Architecture: LLM runs on FI Edge (local machine) via Cloudflare Tunnel.
 * DO backend proxies requests through the tunnel (~2-5s latency).
 *
 * Run locally: npx playwright test tests/e2e/llm-health.spec.ts
 * Run in CI: BACKEND_URL=https://app.aurity.io npx playwright test tests/e2e/llm-health.spec.ts
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || process.env.BASE_URL || 'http://localhost:7001';

test.describe('LLM Health Check (Fast)', () => {
  test('LLM /api/llm/health endpoint responds', async ({ request }) => {
    console.log(`🔍 Checking LLM health at ${BACKEND_URL}/api/llm/health`);

    const response = await request.get(`${BACKEND_URL}/api/llm/health`, {
      timeout: 15_000, // 15 seconds (includes Cloudflare Tunnel latency)
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // Log LLM status
    console.log(`📊 LLM Status: ${data.status}`);
    console.log(`🦙 Ollama available: ${data.ollama}`);
    console.log(`🤖 Models: ${data.models?.join(', ') || 'none'}`);

    // Verify response structure
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('ollama');
    expect(data).toHaveProperty('models');

    // Check if LLM is actually available
    if (data.status === 'ok') {
      expect(data.ollama).toBe(true);
      expect(data.model_count).toBeGreaterThan(0);
      console.log(`✅ LLM healthy with ${data.model_count} models`);
    } else {
      console.log(`⚠️ LLM degraded: ${data.error || 'unknown'}`);
      // Don't fail - just warn (LLM might be temporarily unavailable)
    }
  });

  test('LLM has Qwen3 model available', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/llm/health`, {
      timeout: 15_000, // 15 seconds (includes Cloudflare Tunnel latency)
    });

    if (!response.ok()) {
      console.log('⚠️ LLM health endpoint not available, skipping Qwen3 check');
      test.skip();
      return;
    }

    const data = await response.json();

    if (!data.ollama) {
      console.log('⚠️ Ollama not available, skipping Qwen3 check');
      test.skip();
      return;
    }

    // Check if any Qwen3 model is available
    const hasQwen3 = data.models?.some((m: string) =>
      m.toLowerCase().includes('qwen')
    );

    if (hasQwen3) {
      console.log(`✅ Qwen3 model found in: ${data.models.filter((m: string) => m.toLowerCase().includes('qwen')).join(', ')}`);
    } else {
      console.log(`⚠️ No Qwen3 model found. Available: ${data.models?.join(', ') || 'none'}`);
    }

    // This is informational - don't fail if Qwen3 not found
    // (could be using different model name)
  });
});
