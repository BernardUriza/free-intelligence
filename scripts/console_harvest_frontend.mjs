#!/usr/bin/env node
/**
 * QA: Harvest console logs from discovered frontend routes
 * Input: frontend_routes.txt or argv routes
 * Output: /tmp/fi-artifacts/console-fe-summary.json + per-route logs
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE_URL = process.env.BASE_URL || "http://localhost:9000";
const OUTDIR = "/tmp/fi-artifacts";
const CONSOLE_DIR = path.join(OUTDIR, "console-fe");

fs.mkdirSync(CONSOLE_DIR, { recursive: true });

/**
 * Read routes from file or argv
 */
function readRoutes() {
  const routesFile = path.join(__dirname, "frontend_routes.txt");
  if (fs.existsSync(routesFile)) {
    console.log(`[HARVEST] Reading routes from ${routesFile}`);
    return fs
      .readFileSync(routesFile, "utf-8")
      .split("\n")
      .map(r => r.trim())
      .filter(r => r && r.startsWith("/"));
  }
  if (process.argv.length > 2) {
    console.log(`[HARVEST] Using routes from argv`);
    return process.argv.slice(2).filter(r => r.startsWith("/"));
  }
  console.log(
    `[HARVEST] No routes found. Create ${routesFile} or pass routes as argv`
  );
  return [];
}

/**
 * Sanitize route for filename
 */
const sanitize = route => route.replace(/\//g, "_").replace(/^_/, "") || "root";

/**
 * Harvest console logs from a single route
 */
async function harvestRoute(browser, route) {
  const url = `${BASE_URL}${route}`;
  const filename = sanitize(route);
  const logFile = path.join(CONSOLE_DIR, `${filename}.json`);

  console.log(`[HARVEST] Visiting ${url}`);

  const result = {
    route,
    url,
    status: "pending",
    httpStatus: null,
    logs: [],
    errors: 0,
    warnings: 0,
    duration_ms: 0
  };

  const startTime = Date.now();

  try {
    const page = await browser.newPage();

    // Capture console events
    page.on("console", msg => {
      result.logs.push({
        type: msg.type(),
        text: msg.text(),
        location: msg.location()
      });
      if (msg.type() === "error") result.errors++;
      if (msg.type() === "warning") result.warnings++;
    });

    // Capture request/response for status code
    page.on("response", response => {
      if (response.url() === url) {
        result.httpStatus = response.status();
      }
    });

    // Navigate with timeout
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 10000 });
      result.status = result.httpStatus === 200 ? "ok" : "error";
    } catch (e) {
      result.status = "timeout";
      result.httpStatus = 0;
      result.logs.push({
        type: "error",
        text: `Navigation timeout: ${e.message}`
      });
      result.errors++;
    }

    await page.close();
  } catch (e) {
    result.status = "error";
    result.logs.push({
      type: "error",
      text: `Browser error: ${e.message}`
    });
    result.errors++;
  }

  result.duration_ms = Date.now() - startTime;

  // Write per-route log file
  fs.writeFileSync(logFile, JSON.stringify(result, null, 2));
  console.log(
    `  [HARVEST] ${route} → ${result.status} (${result.errors} errors, ${result.warnings} warnings)`
  );

  return result;
}

// Main execution
const routes = readRoutes();
if (routes.length === 0) {
  console.error("[HARVEST] No routes to harvest. Exiting.");
  process.exit(1);
}

console.log(`[HARVEST] Base URL: ${BASE_URL}`);
console.log(`[HARVEST] Routes: ${routes.length}`);
console.log("");

let browser;
try {
  browser = await chromium.launch();
  const results = [];

  for (const route of routes) {
    const result = await harvestRoute(browser, route);
    results.push({
      route: result.route,
      status: result.status,
      httpStatus: result.httpStatus,
      errors: result.errors,
      warnings: result.warnings,
      logs_count: result.logs.length,
      duration_ms: result.duration_ms,
      log_file: `console-fe/${sanitize(route)}.json`
    });
  }

  // Write summary
  const summary = {
    base: BASE_URL,
    timestamp: new Date().toISOString(),
    routes_tested: routes.length,
    summary: results,
    all_ok: results.every(r => r.status === "ok" && r.errors === 0),
    total_errors: results.reduce((sum, r) => sum + r.errors, 0),
    total_warnings: results.reduce((sum, r) => sum + r.warnings, 0)
  };

  const summaryFile = path.join(OUTDIR, "console-fe-summary.json");
  fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2));

  console.log("");
  console.log(`[HARVEST] Summary saved to ${summaryFile}`);
  console.log(
    `[HARVEST] Routes with status=ok: ${results.filter(r => r.status === "ok").length}/${routes.length}`
  );
  console.log(`[HARVEST] Total errors: ${summary.total_errors}`);
  console.log(`[HARVEST] Total warnings: ${summary.total_warnings}`);
  console.log("");
  console.log(JSON.stringify(summary, null, 2));
} finally {
  if (browser) await browser.close();
}
