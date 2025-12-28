#!/usr/bin/env node

/**
 * Route Validation Script for FI-UI-FEAT-004
 * Validates that all frontend routes load without errors
 */

// Node.js v18+ has native fetch, no import needed

const BASE_URL = process.env.BASE_URL || 'http://localhost:9000';

const ROUTES_TO_TEST = [
  '/',
  '/dashboard',
  '/timeline',
  '/timeline-v2', // This route doesn't exist but is mentioned in the card
  '/audit',
  '/history',
  '/medical-ai',
  '/onboarding',
  '/policy',
  '/test-chunks',
  '/infra/nas-installer'
];

async function testRoute(route) {
  try {
    const response = await fetch(`${BASE_URL}${route}`, {
      method: 'GET',
      headers: {
        'Accept': 'text/html',
      }
    });

    const status = response.status;
    const isOk = status >= 200 && status < 400;

    return {
      route,
      status,
      success: isOk,
      error: isOk ? null : `HTTP ${status}`
    };
  } catch (error) {
    return {
      route,
      status: null,
      success: false,
      error: error.message
    };
  }
}

async function main() {
  console.log('🔍 FI-UI-FEAT-004: Route Validation Report');
  console.log('==========================================');
  console.log(`Testing against: ${BASE_URL}`);
  console.log('');

  const results = await Promise.all(ROUTES_TO_TEST.map(testRoute));

  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);

  console.log('✅ Successful Routes:');
  successful.forEach(r => {
    console.log(`  ${r.route} - HTTP ${r.status}`);
  });

  if (failed.length > 0) {
    console.log('\n❌ Failed Routes:');
    failed.forEach(r => {
      console.log(`  ${r.route} - ${r.error}`);
    });
  }

  console.log('\n📊 Summary:');
  console.log(`  Total Routes Tested: ${results.length}`);
  console.log(`  ✅ Successful: ${successful.length}`);
  console.log(`  ❌ Failed: ${failed.length}`);
  console.log(`  Success Rate: ${((successful.length / results.length) * 100).toFixed(1)}%`);

  // Generate timestamp
  const timestamp = new Date().toISOString();
  console.log(`\n📅 Report Generated: ${timestamp}`);

  // Exit with error if any routes failed
  if (failed.length > 0) {
    console.log('\n⚠️  Some routes failed validation');
    process.exit(1);
  } else {
    console.log('\n✨ All routes validated successfully!');
  }
}

// Check if server is running before testing
fetch(BASE_URL)
  .then(() => {
    console.log(`✓ Server is running at ${BASE_URL}\n`);
    main();
  })
  .catch(() => {
    console.error(`❌ Server is not running at ${BASE_URL}`);
    console.error('Please start the development server with: pnpm dev');
    process.exit(1);
  });