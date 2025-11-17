#!/usr/bin/env node
/**
 * QA: Capture console logs from API endpoints with Playwright
 * Outputs: /tmp/fi-artifacts/console_summary.json + individual endpoint logs
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.BASE_URL || 'http://localhost:7001';
const WAIT_MS = parseInt(process.env.WAIT_MS || '3000', 10);
const epsPath = process.env.ENDPOINTS_FILE || path.join(__dirname, 'endpoints.txt');
const outDir = '/tmp/fi-artifacts/console';

fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync('/tmp/fi-artifacts', { recursive: true });

const endpoints = fs.readFileSync(epsPath, 'utf8')
  .split('\n')
  .map(x => x.trim())
  .filter(Boolean);

console.log(`[QA] Testing endpoints: ${endpoints.join(', ')}`);
console.log(`[QA] BASE_URL: ${BASE}`);
console.log(`[QA] Output: ${outDir}`);
console.log('');

const browser = await chromium.launch({ headless: true });
const summary = [];

for (const ep of endpoints) {
  const url = `${BASE}${ep}`;
  const page = await browser.newPage();
  const logs = [];

  page.on('console', msg => {
    logs.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location()
    });
  });

  let status = 'ok';
  let httpStatus = null;
  let errorCount = 0;
  let warnCount = 0;
  let error = null;

  try {
    console.log(`[QA] Testing ${ep}...`);
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(WAIT_MS);

    if (!resp || !resp.ok()) {
      status = `http_${resp ? resp.status() : 0}`;
      httpStatus = resp ? resp.status() : 0;
    } else {
      httpStatus = 200;
    }

    errorCount = logs.filter(l => l.type === 'error').length;
    warnCount = logs.filter(l => l.type === 'warning').length;

    if (errorCount > 0) status = 'has_errors';

  } catch (e) {
    status = `exception`;
    error = `${e.name}: ${e.message}`;
    errorCount++;
  } finally {
    const slug = ep.replace(/\W+/g, '_') || 'root';
    const consoleData = {
      endpoint: ep,
      url,
      status,
      httpStatus,
      error,
      logs,
      summary: {
        total_logs: logs.length,
        errors: errorCount,
        warnings: warnCount,
        info: logs.filter(l => l.type === 'log').length
      }
    };

    fs.writeFileSync(
      path.join(outDir, `${slug}.json`),
      JSON.stringify(consoleData, null, 2)
    );

    summary.push({
      endpoint: ep,
      url,
      status,
      httpStatus,
      errors: errorCount,
      warnings: warnCount,
      logs_count: logs.length,
      console_file: `console/${slug}.json`
    });

    console.log(`  ✓ ${ep} (status=${status}, errors=${errorCount}, warnings=${warnCount})`);
    await page.close();
  }
}

await browser.close();

fs.writeFileSync('/tmp/fi-artifacts/console_summary.json', JSON.stringify(summary, null, 2));

console.log('');
console.log('═══════════════════════════════════════════════════════════');
console.log('CONSOLE HARVEST SUMMARY');
console.log('═══════════════════════════════════════════════════════════');
console.log(JSON.stringify(summary, null, 2));
console.log('═══════════════════════════════════════════════════════════');

const hasHardErrors = summary.some(s => s.status !== 'ok' || s.errors > 0);
process.exit(hasHardErrors ? 1 : 0);
