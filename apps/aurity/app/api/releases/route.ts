/**
 * Releases API Route
 *
 * Returns available Aurity Desktop releases.
 * In production, this reads from a releases.json file on the server.
 * In development, returns placeholder data.
 */

import { NextResponse } from 'next/server';

interface ReleaseInfo {
  version: string;
  date: string;
  platforms: {
    macos?: {
      url: string;
      size: string;
      sha256: string;
    };
    linux?: {
      url: string;
      size: string;
      sha256: string;
    };
  };
  changelog?: string[];
}

// Placeholder releases (used when releases.json doesn't exist)
const placeholderReleases: ReleaseInfo[] = [
  {
    version: '1.0.0',
    date: '2024-12-28',
    platforms: {
      macos: {
        url: '#coming-soon',
        size: '~150 MB',
        sha256: 'pending',
      },
      linux: {
        url: '#coming-soon',
        size: '~120 MB',
        sha256: 'pending',
      },
    },
    changelog: [
      'Initial release of Aurity Desktop',
      'Offline AI medical assistant powered by Ollama',
      'Local LLM integration (Qwen3, Llama, etc.)',
      'Encrypted local storage in ~/.aurity',
      'Medical consultation transcription',
      'SOAP note generation',
    ],
  },
];

export async function GET() {
  try {
    // In production, try to fetch releases from backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

    // Try to fetch from backend releases endpoint
    try {
      const response = await fetch(`${backendUrl}/api/releases`, {
        next: { revalidate: 60 }, // Cache for 60 seconds
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend not available or endpoint doesn't exist
      console.log('Releases API: Using placeholder data (backend unavailable)');
    }

    // Return placeholder data
    return NextResponse.json({
      releases: placeholderReleases,
      source: 'placeholder',
    });
  } catch (error) {
    console.error('Releases API error:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch releases',
        releases: placeholderReleases,
      },
      { status: 500 }
    );
  }
}
