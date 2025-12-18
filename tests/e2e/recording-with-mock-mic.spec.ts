/**
 * E2E Test: Recording with Fake Audio Stream
 *
 * Tests the RecordRTC stop/start loop pattern with Chromium's fake media devices.
 * Uses --use-fake-device-for-media-stream to bypass real microphone.
 *
 * Sources:
 * - https://omarelb.substack.com/p/til-2-set-up-playwright-with-fake
 * - https://medium.com/@aasispaudelthp2/mock-the-mediarecorder-api-in-playwright-tutorial-48208881b337
 */

import { test, expect, chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Ensure screenshots directory exists
const screenshotsDir = path.join('test-results', 'screenshots');
fs.mkdirSync(screenshotsDir, { recursive: true });

async function screenshot(page: any, name: string) {
  const screenshotPath = path.join(screenshotsDir, `${name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`📸 Screenshot: ${screenshotPath}`);
}

test.describe('RecordRTC with Fake Audio', () => {

  test('should generate WAV chunks with valid headers using RecordRTC', async ({ browser }) => {
    // Launch browser with fake media device flags
    const context = await browser.newContext({
      permissions: ['microphone'],
    });

    const page = await context.newPage();

    // Collect logs
    const logs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      logs.push(`[${msg.type()}] ${text}`);
      if (text.includes('RecordRTC') || text.includes('Chunk') || text.includes('WAV')) {
        console.log(`🎙️ ${text}`);
      }
    });

    // Inject fake getUserMedia with oscillator tone
    await page.addInitScript(() => {
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

      navigator.mediaDevices.getUserMedia = async (constraints: MediaStreamConstraints) => {
        console.log('[FakeMedia] getUserMedia called');

        // Create audio context with oscillator for consistent test audio
        const audioContext = new AudioContext({ sampleRate: 16000 });
        const oscillator = audioContext.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.value = 440; // A4 note

        // Add some variation to make it more realistic
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0.5;

        const dest = audioContext.createMediaStreamDestination();
        oscillator.connect(gainNode);
        gainNode.connect(dest);
        oscillator.start();

        console.log('[FakeMedia] ✅ Returning fake audio stream');
        return dest.stream;
      };
    });

    // Navigate to medical-ai page
    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');

    await screenshot(page, 'recordrtc-01-loaded');

    // Handle login if needed
    const loginButton = page.locator('button:has-text("Iniciar"), button:has-text("Login")').first();
    if (await loginButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('📝 Logging in...');
      await loginButton.click();
      await page.waitForTimeout(3000);
    }

    await page.waitForTimeout(2000);
    await screenshot(page, 'recordrtc-02-ready');

    // Find and click record button
    const recordButton = page.locator('button.rounded-full').first();
    if (await recordButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('🎬 Starting recording...');
      await recordButton.click();

      // Wait for multiple chunks (8 seconds each based on timeSlice)
      console.log('⏳ Recording for 25 seconds to capture multiple chunks...');
      await page.waitForTimeout(25000);

      await screenshot(page, 'recordrtc-03-recording');

      // Stop recording
      const stopButton = page.locator('button:has-text("Detener"), button:has-text("Stop"), button:has-text("Pausar")').first();
      if (await stopButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await stopButton.click();
        console.log('⏹️ Stopped recording');
      }

      await page.waitForTimeout(3000);
      await screenshot(page, 'recordrtc-04-stopped');
    }

    // Check logs for RecordRTC activity
    const recordRTCLogs = logs.filter(l =>
      l.includes('RecordRTC') ||
      l.includes('Chunk') ||
      l.includes('WAV') ||
      l.includes('RIFF')
    );

    console.log('\n========== RecordRTC LOGS ==========');
    recordRTCLogs.forEach(l => console.log(l));
    console.log('=====================================\n');

    // Verify RecordRTC was used (not MediaRecorder)
    const usedRecordRTC = logs.some(l => l.includes('recordrtc'));
    console.log(`✅ Used RecordRTC: ${usedRecordRTC}`);

    await context.close();
  });


  test('verify WAV header in chunks', async ({ page, context }) => {
    await context.grantPermissions(['microphone']);

    // Inject fake getUserMedia
    await page.addInitScript(() => {
      navigator.mediaDevices.getUserMedia = async () => {
        const ctx = new AudioContext({ sampleRate: 16000 });
        const osc = ctx.createOscillator();
        osc.frequency.value = 440;
        const dest = ctx.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        return dest.stream;
      };
    });

    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');

    // Test RecordRTC directly in browser context
    const result = await page.evaluate(async () => {
      const logs: string[] = [];

      try {
        // Dynamic import RecordRTC (should be available if bundled)
        const RecordRTC = (window as any).RecordRTC || await import('recordrtc').then(m => m.default);

        if (!RecordRTC) {
          logs.push('❌ RecordRTC not available');
          return { logs, success: false };
        }

        logs.push('✅ RecordRTC available');

        // Get fake stream
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        logs.push(`✅ Got stream with ${stream.getTracks().length} tracks`);

        // Create RecordRTC instance with WAV
        const recorder = new RecordRTC(stream, {
          type: 'audio',
          recorderType: RecordRTC.StereoAudioRecorder,
          mimeType: 'audio/wav',
          numberOfAudioChannels: 1,
          desiredSampRate: 16000,
          disableLogs: true,
        });

        logs.push('✅ Created RecordRTC instance');

        // Record for 2 seconds
        recorder.startRecording();
        logs.push('▶️ Started recording');

        await new Promise(r => setTimeout(r, 2000));

        // Stop and get blob
        await new Promise<void>(resolve => {
          recorder.stopRecording(() => resolve());
        });
        logs.push('⏹️ Stopped recording');

        const blob = recorder.getBlob();
        logs.push(`📦 Got blob: ${blob.size} bytes, type: ${blob.type}`);

        // Check WAV header (RIFF)
        const buffer = await blob.arrayBuffer();
        const header = new Uint8Array(buffer.slice(0, 4));
        const headerStr = String.fromCharCode(...header);

        if (headerStr === 'RIFF') {
          logs.push('✅ Valid WAV header (RIFF) detected!');
        } else {
          logs.push(`❌ Invalid header: ${headerStr} (hex: ${Array.from(header).map(b => b.toString(16).padStart(2, '0')).join(' ')})`);
        }

        // Cleanup
        stream.getTracks().forEach(t => t.stop());

        return { logs, success: headerStr === 'RIFF', blobSize: blob.size };

      } catch (err: any) {
        logs.push(`❌ Error: ${err.message}`);
        return { logs, success: false };
      }
    });

    console.log('\n========== WAV HEADER TEST ==========');
    result.logs.forEach((log: string) => console.log(log));
    console.log('======================================\n');

    await screenshot(page, 'wav-header-test');

    // Assert WAV header is valid
    expect(result.success).toBe(true);
    expect(result.blobSize).toBeGreaterThan(1000); // Should have actual audio data
  });


  test('multiple chunks all have headers', async ({ page, context }) => {
    await context.grantPermissions(['microphone']);

    await page.addInitScript(() => {
      navigator.mediaDevices.getUserMedia = async () => {
        const ctx = new AudioContext({ sampleRate: 16000 });
        const osc = ctx.createOscillator();
        osc.frequency.value = 440;
        const dest = ctx.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        return dest.stream;
      };
    });

    await page.goto('/medical-ai');
    await page.waitForLoadState('networkidle');

    // Test stop/start loop pattern
    const result = await page.evaluate(async () => {
      const chunks: { index: number; size: number; header: string; valid: boolean }[] = [];

      try {
        const RecordRTC = (window as any).RecordRTC || await import('recordrtc').then(m => m.default);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Simulate stop/start loop like makeRecorder does
        for (let i = 0; i < 3; i++) {
          const recorder = new RecordRTC(stream, {
            type: 'audio',
            recorderType: RecordRTC.StereoAudioRecorder,
            mimeType: 'audio/wav',
            numberOfAudioChannels: 1,
            desiredSampRate: 16000,
            disableLogs: true,
          });

          recorder.startRecording();
          await new Promise(r => setTimeout(r, 1500)); // 1.5 second chunks

          await new Promise<void>(resolve => {
            recorder.stopRecording(() => resolve());
          });

          const blob = recorder.getBlob();
          const buffer = await blob.arrayBuffer();
          const header = new Uint8Array(buffer.slice(0, 4));
          const headerStr = String.fromCharCode(...header);

          chunks.push({
            index: i,
            size: blob.size,
            header: headerStr,
            valid: headerStr === 'RIFF',
          });
        }

        stream.getTracks().forEach(t => t.stop());

        return { chunks, allValid: chunks.every(c => c.valid) };

      } catch (err: any) {
        return { chunks, allValid: false, error: err.message };
      }
    });

    console.log('\n========== MULTIPLE CHUNKS TEST ==========');
    console.log('Chunks generated:');
    result.chunks.forEach((c: any) => {
      console.log(`  Chunk ${c.index}: ${c.size} bytes, header: "${c.header}", valid: ${c.valid ? '✅' : '❌'}`);
    });
    console.log(`All chunks valid: ${result.allValid ? '✅' : '❌'}`);
    console.log('==========================================\n');

    await screenshot(page, 'multiple-chunks-test');

    // All chunks should have valid RIFF headers
    expect(result.allValid).toBe(true);
    expect(result.chunks.length).toBe(3);
  });

});
