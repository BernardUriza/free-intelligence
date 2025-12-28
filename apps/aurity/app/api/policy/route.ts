/**
 * Policy API Route
 * Card: FI-UI-FEAT-204
 *
 * Proxies policy configuration from backend FastAPI service
 */

import { NextResponse } from 'next/server';

// Required for static export (Next.js 16 with output: 'export')
export const dynamic = 'force-static';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/policy`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Cache for static export (Next.js 16 requirement)
      cache: 'force-cache',
    });

    if (!response.ok) {
      return NextResponse.json(
        {
          error: `Backend returned ${response.status}: ${response.statusText}`,
          detail: 'Failed to fetch policy from backend',
        },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error) {
    console.error('[Policy API] Failed to fetch policy:', error);

    return NextResponse.json(
      {
        error: 'Failed to connect to backend',
        detail: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}
