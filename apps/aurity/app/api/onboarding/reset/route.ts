/**
 * Onboarding Reset Endpoint
 *
 * Utility endpoint to reset onboarding state for testing/debugging
 * DELETE /api/onboarding/reset
 */

import { NextResponse } from 'next/server';

// Required for static export (Next.js 16 with output: 'export')
export const dynamic = 'force-static';

export async function DELETE() {
  // Return instructions for client-side reset
  // (LocalStorage can only be accessed client-side)

  const resetScript = `
    localStorage.removeItem('fi_onboarding_progress');
    localStorage.removeItem('fi_onboarding_conversation');
    localStorage.removeItem('aurity_onboarding_completed');
    localStorage.removeItem('fi_onboarding_survey');
  `;

  return NextResponse.json({
    success: true,
    message: 'Execute this script in browser console to reset onboarding',
    script: resetScript,
    instructions: [
      '1. Open browser console (F12 or Cmd+Option+I)',
      '2. Paste the script',
      '3. Press Enter',
      '4. Reload the page',
    ],
  });
}

export async function GET() {
  // Check onboarding status
  return NextResponse.json({
    message: 'Use DELETE method to get reset instructions',
    endpoints: {
      reset: 'DELETE /api/onboarding/reset',
      check: 'GET /api/onboarding/status (client-side only)',
    },
  });
}
