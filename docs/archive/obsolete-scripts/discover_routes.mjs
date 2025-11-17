#!/usr/bin/env node
/**
 * QA: Discover Next.js frontend routes from filesystem (app/pages) + crawl
 * Outputs: /tmp/fi-artifacts/frontend_routes.{txt,json}
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.FE_ROOT || path.join(__dirname, "..", "apps", "aurity");
const MAX = parseInt(process.env.MAX_ROUTES || "50", 10);
const OUTDIR = "/tmp/fi-artifacts";

fs.mkdirSync(OUTDIR, { recursive: true });

const exists = p => {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
};

function fromFilesystem() {
  const routes = new Set();
  const appDir = path.join(ROOT, "app");
  const pagesDir = path.join(ROOT, "pages");

  // Convert [param] to test placeholder
  const dyn = seg => seg.replace(/\[.*?\]/g, "test");

  const pushRoute = r => {
    r = r.replace(/\/index$/, "/");
    if (!r.startsWith("/")) r = "/" + r;
    routes.add(r);
  };

  // Walk app directory (Next.js 13+)
  function walkApp(dir, base = "") {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.isDirectory()) {
        const d = path.join(dir, e.name);
        const seg = dyn(e.name);
        walkApp(d, path.join(base, seg));
      } else if (/^page\.(tsx|jsx|mdx?)$/.test(e.name)) {
        pushRoute(base || "/");
      }
    }
  }

  // Walk pages directory (Next.js 12 and below)
  function walkPages(dir, base = "") {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const d = path.join(dir, e.name);
      if (e.isDirectory()) {
        walkPages(d, path.join(base, dyn(e.name)));
      } else if (/^(index|[^.]+)\.(tsx|jsx|js)$/.test(e.name)) {
        const name = path.parse(e.name).name;
        pushRoute(path.join(base, name === "index" ? "" : name));
      }
    }
  }

  if (exists(appDir)) {
    console.log(`[DISCOVER] Scanning app directory: ${appDir}`);
    walkApp(appDir, "");
  }
  if (exists(pagesDir)) {
    console.log(`[DISCOVER] Scanning pages directory: ${pagesDir}`);
    walkPages(pagesDir, "");
  }

  return Array.from(routes);
}

async function fromCrawl(base = "http://localhost:9000", limit = 30) {
  console.log(`[DISCOVER] Crawling from ${base} (limit: ${limit})`);
  const seen = new Set(["/", "/health"]);
  const queue = ["/"];
  const inScope = href =>
    href.startsWith("/") &&
    !href.startsWith("/_next") &&
    !href.startsWith("/api") &&
    !href.startsWith("/__") &&
    !href.includes("?") &&
    !href.includes("#");

  while (queue.length && seen.size < limit) {
    const route = queue.shift();
    try {
      const res = await fetch(base + route, { timeout: 5000 });
      const html = await res.text();
      const hrefs = [...html.matchAll(/href="([^"]+)"/g)].map(m => m[1]).filter(inScope);
      for (const h of hrefs) {
        if (!seen.has(h)) {
          seen.add(h);
          queue.push(h);
        }
      }
    } catch (e) {
      console.log(`  [CRAWL] Error on ${route}: ${e.message}`);
    }
  }

  return Array.from(seen);
}

// Main execution
const base = process.env.BASE_URL || "http://localhost:9000";
console.log(`[DISCOVER] Root: ${ROOT}`);
console.log(`[DISCOVER] Base URL: ${base}`);
console.log("");

const fsRoutes = fromFilesystem();
console.log(`[DISCOVER] Filesystem routes: ${fsRoutes.length}`);

const crawlRoutes = await fromCrawl(base, 30);
console.log(`[DISCOVER] Crawled routes: ${crawlRoutes.length}`);

const merged = Array.from(new Set([...fsRoutes, ...crawlRoutes]))
  .sort()
  .slice(0, MAX);

console.log(`[DISCOVER] Total unique routes: ${merged.length}`);
console.log("");

// Write outputs
fs.writeFileSync(path.join(OUTDIR, "frontend_routes.txt"), merged.join("\n"));
fs.writeFileSync(
  path.join(OUTDIR, "frontend_routes.json"),
  JSON.stringify(
    {
      base,
      timestamp: new Date().toISOString(),
      count: merged.length,
      routes: merged
    },
    null,
    2
  )
);

console.log(`[DISCOVER] Routes saved to ${OUTDIR}/frontend_routes.{txt,json}`);
console.log(JSON.stringify({ base, discovered: merged.length, routes: merged }, null, 2));
