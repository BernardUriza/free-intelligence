#!/usr/bin/env node
/**
 * Generate TypeScript API client from FastAPI OpenAPI specs
 *
 * Usage: node scripts/generate-api-client.mjs
 *
 * Requires backend running at http://localhost:7001
 */

import { createClient } from '@hey-api/openapi-ts';
import { writeFileSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = dirname(__dirname);

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:7001';

async function fetchOpenAPISpec(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
  }
  return response.json();
}

async function generateSDK(specUrl, outputPath, clientName) {
  console.log(`\n📥 Fetching OpenAPI spec from ${specUrl}...`);

  try {
    const spec = await fetchOpenAPISpec(specUrl);

    // Save spec to temp file for @hey-api/openapi-ts
    const tempSpecPath = `/tmp/${clientName}-openapi.json`;
    writeFileSync(tempSpecPath, JSON.stringify(spec, null, 2));
    console.log(`   ✅ Spec saved (${spec.paths ? Object.keys(spec.paths).length : 0} endpoints)`);

    console.log(`\n🔨 Generating TypeScript SDK to ${outputPath}...`);

    await createClient({
      input: tempSpecPath,
      output: outputPath,
      client: '@hey-api/client-fetch',
    });

    console.log(`   ✅ TypeScript SDK generated`);
  } catch (error) {
    console.error(`   ❌ Error generating ${clientName}: ${error.message}`);
    throw error;
  }
}

async function main() {
  console.log('🚀 FastAPI OpenAPI → TypeScript SDK Generator\n');
  console.log(`Backend: ${BACKEND_URL}`);

  // Check backend is running
  try {
    const healthCheck = await fetch(`${BACKEND_URL}/health`);
    if (!healthCheck.ok) {
      throw new Error('Backend health check failed');
    }
    console.log('✅ Backend is running\n');
  } catch (error) {
    console.error('❌ Backend is not running. Start it with: make run');
    process.exit(1);
  }

  const apis = [
    {
      name: 'public-api',
      url: `${BACKEND_URL}/api/openapi.json`,
      output: `${PROJECT_ROOT}/apps/aurity/src/api/public`,
    },
    {
      name: 'internal-api',
      url: `${BACKEND_URL}/internal/openapi.json`,
      output: `${PROJECT_ROOT}/apps/aurity/src/api/internal`,
    },
  ];

  for (const api of apis) {
    await generateSDK(api.url, api.output, api.name);
  }

  // Create index.ts barrel export
  const indexPath = `${PROJECT_ROOT}/apps/aurity/src/api/index.ts`;
  const indexContent = `/**
 * Auto-generated API clients from FastAPI OpenAPI specs
 *
 * To regenerate: npm run generate:api
 */

export * from './public';
export * from './internal';
`;

  mkdirSync(dirname(indexPath), { recursive: true });
  writeFileSync(indexPath, indexContent);
  console.log(`\n✅ Created barrel export: src/api/index.ts`);

  console.log('\n🎉 API client generation complete!\n');
  console.log('Usage in your Next.js app:');
  console.log('  import { PublicApiService } from "@/api/public";');
  console.log('  import { InternalApiService } from "@/api/internal";\n');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
