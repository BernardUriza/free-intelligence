#!/usr/bin/env npx ts-node
/**
 * Get Auth0 Token Script
 *
 * Opens browser, waits for login, captures token, and outputs it for curl testing.
 *
 * Usage:
 *   npx ts-node scripts/get-auth-token.ts
 *   # Or with npx playwright:
 *   npx playwright test scripts/get-auth-token.ts --project=chromium --headed
 *
 * After getting the token, test with:
 *   export TOKEN='<output>'
 *   curl -s http://localhost:7001/api/admin/licenses/features -H "Authorization: Bearer $TOKEN"
 */

import { chromium } from 'playwright';

const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:9000';

async function main() {
  console.log('🚀 Opening browser for Auth0 login...\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  let capturedToken: string | null = null;

  // Intercept API requests to capture the token
  page.on('request', (request) => {
    const authHeader = request.headers()['authorization'];
    if (authHeader && authHeader.startsWith('Bearer ') && !capturedToken) {
      capturedToken = authHeader.replace('Bearer ', '');
      console.log('\n✅ Token captured!\n');
      console.log('=' .repeat(80));
      console.log('TOKEN (for curl):');
      console.log('=' .repeat(80));
      console.log(capturedToken);
      console.log('=' .repeat(80));
      console.log('\n📋 Copy the token above and use it like this:');
      console.log(`
export TOKEN='${capturedToken.substring(0, 50)}...'

# Test features endpoint:
curl -s http://localhost:7001/api/admin/licenses/features \\
  -H "Authorization: Bearer \$TOKEN" | jq

# Test generate endpoint:
curl -s -X POST http://localhost:7001/api/admin/licenses/generate \\
  -H "Authorization: Bearer \$TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "clinic_id": "test-clinic",
    "clinic_name": "Test Clinic",
    "auth0_domain": "dev-1r4daup7ofj7q6gn.us.auth0.com",
    "auth0_client_id": "rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp",
    "features": ["soap", "timeline"],
    "expires_days": 30
  }' | jq
`);
    }
  });

  // Navigate to app
  await page.goto(BASE_URL);

  console.log('📝 Please log in with your Auth0 credentials...');
  console.log('   The script will capture the token after you log in.\n');

  // Wait for user to log in and make an API request
  // The token will be captured by the request interceptor
  await page.waitForTimeout(120000); // Wait up to 2 minutes

  if (!capturedToken) {
    console.log('\n⚠️  No token captured. Make sure to log in and navigate to a page that makes API calls.');
  }

  await browser.close();
}

main().catch(console.error);
