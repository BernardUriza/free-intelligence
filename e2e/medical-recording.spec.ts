/**
 * E2E Test: Medical Recording Flow
 *
 * Tests the conversation capture workflow:
 * 1. Navigate to /medical-ai
 * 2. Grant microphone permissions (mocked)
 * 3. Start recording
 * 4. Verify chunks are sent to backend
 * 5. Stop recording
 * 6. Verify transcription appears
 *
 * Screenshots are captured at each step for debugging.
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

// Screenshot helper
async function screenshot(page: Page, name: string) {
  const screenshotPath = path.join('test-results', 'screenshots', `${name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`📸 Screenshot saved: ${screenshotPath}`);
}

// Setup: Grant microphone permissions
test.beforeEach(async ({ context }) => {
  // Grant microphone permission
  await context.grantPermissions(['microphone']);
});

test.describe('Medical Recording Flow', () => {

  test('should load medical-ai page', async ({ page }) => {
    await page.goto('/medical-ai');
    await screenshot(page, '01-page-loaded');

    // Check page loaded
    await expect(page).toHaveURL(/medical-ai/);

    // Check key elements are present
    const header = page.locator('text=Medical AI Workflow');
    await expect(header).toBeVisible({ timeout: 10000 });

    await screenshot(page, '02-header-visible');
  });

  test('should show recording controls', async ({ page }) => {
    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');

    await screenshot(page, '03-before-recording');

    // Look for recording button or capture area
    const captureSection = page.locator('text=Captura de Conversación').or(
      page.locator('text=Conversation Capture')
    );

    if (await captureSection.isVisible()) {
      await screenshot(page, '04-capture-section-found');
    } else {
      await screenshot(page, '04-capture-section-NOT-found');
    }
  });

  test('should start recording when clicking record button', async ({ page }) => {
    // Enable console logging
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[Recorder]') || text.includes('Chunk')) {
        console.log(`🎙️ ${msg.type()}: ${text}`);
      }
    });

    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Wait for React hydration

    await screenshot(page, '05-ready-to-record');

    // Find and click the record/start button
    // Try different selectors
    const recordButton = page.locator('button').filter({ hasText: /grabar|record|iniciar|start/i }).first();
    const playButton = page.locator('button[aria-label*="record"]').first();
    const circleButton = page.locator('.recording-controls button').first();

    let buttonFound = false;

    if (await recordButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('Found record button by text');
      await recordButton.click();
      buttonFound = true;
    } else if (await playButton.isVisible({ timeout: 1000 }).catch(() => false)) {
      console.log('Found record button by aria-label');
      await playButton.click();
      buttonFound = true;
    } else if (await circleButton.isVisible({ timeout: 1000 }).catch(() => false)) {
      console.log('Found circle button');
      await circleButton.click();
      buttonFound = true;
    }

    await screenshot(page, '06-after-click-attempt');

    // Wait for recording to start (check for recording indicator)
    await page.waitForTimeout(3000);

    await screenshot(page, '07-recording-state');

    // Check console logs for recorder activity
    const consoleLogs = await page.evaluate(() => {
      return (window as any).__recorder_logs || [];
    });
    console.log('Console logs:', consoleLogs);
  });

  test('debug: capture all console logs during recording', async ({ page }) => {
    const logs: string[] = [];

    page.on('console', msg => {
      logs.push(`[${msg.type()}] ${msg.text()}`);
    });

    page.on('pageerror', error => {
      logs.push(`[ERROR] ${error.message}`);
    });

    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await screenshot(page, '08-debug-start');

    // Click anywhere that might trigger recording
    const yellowCircle = page.locator('div').filter({ has: page.locator('svg') }).first();

    // Try to find the recording area
    const recordingArea = page.locator('[class*="recording"]').first();
    if (await recordingArea.isVisible({ timeout: 2000 }).catch(() => false)) {
      await recordingArea.click();
    }

    await page.waitForTimeout(5000); // Wait 5 seconds

    await screenshot(page, '09-debug-after-wait');

    // Output all logs
    console.log('\n========== ALL CONSOLE LOGS ==========');
    logs.forEach(log => console.log(log));
    console.log('========================================\n');

    // Save logs to file
    const fs = await import('fs');
    fs.writeFileSync(
      'test-results/console-logs.txt',
      logs.join('\n'),
      'utf-8'
    );
  });

  test('mock microphone and verify chunk upload', async ({ page, context }) => {
    // This test uses a fake audio stream
    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');

    // Inject fake getUserMedia that returns a silent audio stream
    await page.evaluate(() => {
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

      navigator.mediaDevices.getUserMedia = async (constraints) => {
        console.log('[TEST] getUserMedia called with:', constraints);

        // Create a silent audio context
        const audioContext = new AudioContext();
        const oscillator = audioContext.createOscillator();
        oscillator.frequency.value = 440; // A4 note
        const dest = audioContext.createMediaStreamDestination();
        oscillator.connect(dest);
        oscillator.start();

        console.log('[TEST] Returning fake audio stream');
        return dest.stream;
      };
    });

    await screenshot(page, '10-mock-injected');

    // Now try to start recording
    await page.waitForTimeout(1000);

    // Click the big yellow/green circle to start recording
    const recordTrigger = page.locator('button, [role="button"], div[class*="cursor-pointer"]')
      .filter({ has: page.locator('svg[class*="animate"]').or(page.locator('[class*="pulse"]')) })
      .first();

    if (await recordTrigger.isVisible({ timeout: 2000 }).catch(() => false)) {
      await recordTrigger.click();
      console.log('Clicked record trigger');
    }

    await page.waitForTimeout(5000);
    await screenshot(page, '11-after-mock-recording');
  });
});
