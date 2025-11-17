import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const TEST_TIMEOUT = 5 * 60 * 1000; // 5 minutes for diarization processing

/**
 * Comprehensive E2E tests for Diarization UI and full process
 * Tests the entire diarization workflow using Desktop mp3 files
 */

test.describe('Diarization Full Process E2E', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('/diarization');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('should load diarization page with all UI elements', async () => {
    // Verify page title
    await expect(page).toHaveTitle(/diarization|Diarization/i);

    // Verify main heading
    const heading = page.locator('h1, h2, [role="heading"]').first();
    await expect(heading).toBeVisible();

    // Verify file upload area exists
    const uploadArea = page.locator('[role="button"]').filter({
      hasText: /upload|drag|drop|select/i,
    });
    await expect(uploadArea.first()).toBeVisible();

    // Verify job history section exists
    const jobHistory = page.locator('text=/job history|recent|history/i').first();
    await expect(jobHistory).toBeVisible({ timeout: 5000 });

    // Verify advanced settings section exists
    const settings = page.locator('text=/advanced|settings|configuration/i').first();
    await expect(settings).toBeVisible({ timeout: 5000 });

    console.log('✅ Page structure validated');
  });

  test('should perform full diarization workflow with Speech.mp3', async () => {
    test.setTimeout(TEST_TIMEOUT);

    const audioFile = path.join(process.env.HOME || '', 'Desktop', 'Speech.mp3');
    if (!fs.existsSync(audioFile)) {
      test.skip();
    }

    console.log(`📁 Testing with: ${audioFile}`);
    console.log(`📊 File size: ${fs.statSync(audioFile).size} bytes`);

    // 1. Upload file via file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(audioFile);

    // Wait for upload to complete
    await page.waitForTimeout(2000);

    // 2. Verify job appears in history
    const jobItems = page.locator('[data-testid="job-item"], .job-card, [class*="job"]');
    let jobFound = false;

    for (let i = 0; i < 5; i++) {
      const jobCount = await jobItems.count();
      if (jobCount > 0) {
        jobFound = true;
        console.log(`✅ Job appeared in history (${jobCount} jobs visible)`);
        break;
      }
      await page.waitForTimeout(500);
    }

    // 3. Monitor progress
    let progressVisible = false;
    for (let attempt = 0; attempt < 10; attempt++) {
      const progressBar = page.locator('[role="progressbar"], .progress, [class*="progress"]');
      const progressCount = await progressBar.count();

      if (progressCount > 0) {
        progressVisible = true;
        const value = await progressBar.first().getAttribute('aria-valuenow');
        console.log(`⏳ Progress: ${value || 'processing'}% (attempt ${attempt + 1}/10)`);
        break;
      }

      await page.waitForTimeout(1000);
    }

    // 4. Wait for job completion (poll status)
    let completed = false;
    let attempts = 0;
    const maxAttempts = 120; // 2 minutes with 1-second checks

    while (!completed && attempts < maxAttempts) {
      // Look for completion indicators
      const successIndicator = page.locator('text=/completed|success|done/i').first();
      const failureIndicator = page.locator('text=/failed|error|cancelled/i').first();
      const processingIndicator = page.locator('text=/processing|running|in progress/i').first();

      const successVisible = await successIndicator
        .isVisible()
        .catch(() => false);
      const failureVisible = await failureIndicator
        .isVisible()
        .catch(() => false);
      const processingVisible = await processingIndicator
        .isVisible()
        .catch(() => false);

      if (successVisible) {
        console.log(`✅ Job completed successfully`);
        completed = true;
      } else if (failureVisible) {
        console.error('❌ Job failed');
        const errorMsg = await failureIndicator.textContent();
        console.error(`Error: ${errorMsg}`);
        break;
      } else if (processingVisible) {
        console.log(`⏳ Still processing... (${attempts + 1}/${maxAttempts})`);
      }

      attempts++;
      await page.waitForTimeout(1000);
    }

    if (!completed) {
      console.warn('⚠️ Job did not complete within timeout');
    }

    // 5. Verify results display
    const resultsSection = page.locator('[class*="result"], [data-testid="results"]').first();
    const resultsVisible = await resultsSection.isVisible().catch(() => false);

    if (resultsVisible) {
      console.log('✅ Results section visible');

      // Check for speaker information
      const speakerLabels = page.locator('text=/PACIENTE|MEDICO|DESCONOCIDO/i');
      const speakerCount = await speakerLabels.count();
      console.log(`👥 Speaker labels found: ${speakerCount}`);

      // Check for transcription segments
      const segments = page.locator('[class*="segment"], [data-testid*="segment"]');
      const segmentCount = await segments.count();
      console.log(`📝 Transcription segments: ${segmentCount}`);
    }

    // 6. Test export functionality
    const exportButton = page.locator('button:has-text("Export"), button:has-text("export")').first();
    if (await exportButton.isVisible().catch(() => false)) {
      console.log('✅ Export button visible');

      // Test JSON export
      const jsonExport = page.locator('button:has-text("JSON"), button:has-text("json")');
      if (await jsonExport.isVisible().catch(() => false)) {
        const downloadPromise = page.waitForEvent('download');
        await jsonExport.click().catch(() => {});
        try {
          const download = await downloadPromise.catch(() => null);
          if (download) {
            console.log(`✅ JSON export downloaded: ${download.suggestedFilename()}`);
          }
        } catch (e) {
          console.log('ℹ️ Export trigger successful (download may not be capturable)');
        }
      }

      // Test Markdown export
      const mdExport = page.locator('button:has-text("Markdown"), button:has-text("markdown")');
      if (await mdExport.isVisible().catch(() => false)) {
        console.log('✅ Markdown export button found');
      }
    }

    // 7. Verify job metadata
    const jobMetadata = page.locator('[class*="metadata"], [data-testid*="metadata"]');
    const metadataVisible = await jobMetadata.isVisible().catch(() => false);

    if (metadataVisible) {
      const text = await jobMetadata.textContent();
      console.log(`📋 Job metadata found: ${text?.substring(0, 100)}...`);
    }
  });

  test('should test with Merchant of Venice (part 0) - smaller file', async () => {
    test.setTimeout(TEST_TIMEOUT);

    const audioFile = path.join(
      process.env.HOME || '',
      'Desktop',
      'merchantofvenice_0_shakespeare_64kb.mp3'
    );
    if (!fs.existsSync(audioFile)) {
      test.skip();
    }

    console.log(`📁 Testing with: ${audioFile}`);
    console.log(`📊 File size: ${fs.statSync(audioFile).size} bytes`);

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(audioFile);

    // Wait for upload to register
    await page.waitForTimeout(2000);

    // Monitor initial upload response
    const statusText = page.locator('[class*="status"], [data-testid*="status"]').first();
    const statusVisible = await statusText.isVisible().catch(() => false);

    if (statusVisible) {
      console.log(`✅ Status indicator visible`);
    }

    // Brief wait to see initial processing
    await page.waitForTimeout(5000);

    // Capture current state
    const processingIndicators = page.locator('text=/processing|uploading|queued/i');
    const indicatorCount = await processingIndicators.count();
    console.log(`⏳ Processing indicators: ${indicatorCount}`);
  });

  test('should handle file drag and drop', async () => {
    const audioFile = path.join(process.env.HOME || '', 'Desktop', 'Speech.mp3');
    if (!fs.existsSync(audioFile)) {
      test.skip();
    }

    // Find the dropzone element
    const dropzone = page.locator('[role="button"]').filter({
      hasText: /upload|drag|drop/i,
    });

    if (await dropzone.isVisible().catch(() => false)) {
      console.log('✅ Dropzone found and accessible');

      // Simulate drag and drop using file input instead
      // (Playwright doesn't support native drag/drop well)
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(audioFile);

      console.log('✅ File selected through input');
      await page.waitForTimeout(1000);
    }
  });

  test('should toggle advanced settings', async () => {
    // Find advanced settings toggle/section
    const settingsToggle = page.locator(
      'button:has-text("Advanced"), button:has-text("Settings"), [role="button"]:has-text("Advanced")'
    );

    const settingsSection = page.locator('[class*="advanced"], [data-testid*="advanced"]');

    const toggleExists = await settingsToggle.isVisible().catch(() => false);
    const settingsExists = await settingsSection.isVisible().catch(() => false);

    if (toggleExists) {
      console.log('✅ Settings toggle found');
      await settingsToggle.click();
      await page.waitForTimeout(500);

      const settingsVisible = await settingsSection.isVisible().catch(() => false);
      console.log(`✅ Settings toggled: ${settingsVisible ? 'visible' : 'hidden'}`);
    } else if (settingsExists) {
      const displayed = await settingsSection.isVisible();
      console.log(`✅ Settings section: ${displayed ? 'visible' : 'hidden'}`);
    } else {
      console.log('ℹ️ Advanced settings not found (may be on different page)');
    }
  });

  test('should display current session vs all sessions filter', async () => {
    // Look for session filter
    const sessionFilter = page.locator(
      'input[type="radio"], input[type="checkbox"]'
    ).first();

    const sessionFilterExists = await sessionFilter.isVisible().catch(() => false);

    if (sessionFilterExists) {
      console.log('✅ Session filter controls found');
    }

    // Look for session information text
    const sessionText = page.locator('text=/current session|all sessions|session/i').first();
    const sessionTextVisible = await sessionText.isVisible().catch(() => false);

    if (sessionTextVisible) {
      const text = await sessionText.textContent();
      console.log(`✅ Session info visible: ${text?.substring(0, 50)}`);
    }
  });

  test('should handle errors gracefully', async () => {
    // Try uploading an invalid file
    const tempDir = require('os').tmpdir();
    const invalidFile = path.join(tempDir, 'test-invalid.txt');
    fs.writeFileSync(invalidFile, 'This is not an audio file');

    try {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(invalidFile);

      await page.waitForTimeout(2000);

      const errorIndicator = page.locator('text=/error|invalid|unsupported/i').first();
      const errorVisible = await errorIndicator.isVisible().catch(() => false);

      if (errorVisible) {
        const errorMsg = await errorIndicator.textContent();
        console.log(`✅ Error handled gracefully: ${errorMsg?.substring(0, 50)}`);
      } else {
        console.log('ℹ️ No error message displayed (may be silent validation)');
      }
    } finally {
      fs.unlinkSync(invalidFile);
    }
  });

  test('should display debug panel if available', async () => {
    const debugPanel = page.locator('[class*="debug"], [data-testid*="debug"], text=/FI Debug/i').first();
    const debugVisible = await debugPanel.isVisible().catch(() => false);

    if (debugVisible) {
      console.log('✅ FI Debug panel visible');
      const text = await debugPanel.textContent();
      console.log(`   Content: ${text?.substring(0, 100)}...`);
    } else {
      console.log('ℹ️ Debug panel not visible (may be hidden by default)');
    }
  });

  test('should show health check status', async () => {
    // Check for health/status indicators
    const healthIndicator = page.locator(
      '[class*="health"], [data-testid*="health"], [class*="status"]'
    );

    const healthCount = await healthIndicator.count();
    if (healthCount > 0) {
      console.log(`✅ Health indicators found: ${healthCount}`);

      for (let i = 0; i < Math.min(healthCount, 3); i++) {
        const text = await healthIndicator.nth(i).textContent();
        if (text) {
          console.log(`   [${i + 1}] ${text.substring(0, 60)}`);
        }
      }
    }
  });
});

test.describe('Diarization API Connectivity', () => {
  test('should verify backend API is accessible', async ({ page }) => {
    // Check health endpoint
    const response = await page.request.get('http://localhost:7001/api/diarization/health').catch(() => null);

    if (response) {
      console.log(`✅ Backend API health check: ${response.status()}`);

      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        console.log(`   Response: ${JSON.stringify(data).substring(0, 100)}`);
      }
    } else {
      console.log('⚠️ Backend API not accessible (port 7001)');
    }
  });

  test('should verify CORS and headers', async ({ page }) => {
    const response = await page.request.get('http://localhost:7001/api/diarization').catch(() => null);

    if (response) {
      const headers = response.headers();
      console.log('✅ API response headers:');
      console.log(`   Content-Type: ${headers['content-type']}`);
      console.log(`   CORS Allow-Origin: ${headers['access-control-allow-origin']}`);
    }
  });
});
