/**
 * Releases API Route
 *
 * Returns available Aurity Desktop releases.
 * In production, this reads from a releases.json file on the server.
 * In development, returns placeholder data.
 */

import { NextResponse } from 'next/server';

// Required for static export
export const dynamic = 'force-static';

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
        url: 'https://app.aurity.io/downloads/Aurity-1.0.0-arm64.dmg',
        size: '96 MB',
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
      'Auth0 OAuth 2.0 + PKCE authentication',
      'Offline AI medical assistant powered by Ollama',
      'Local LLM integration (Qwen3, Llama, etc.)',
      'Encrypted local storage in ~/.aurity',
      'Secure token storage in OS Keychain',
    ],
  },
];

export async function GET() {
  // Static export: return hardcoded releases
  return NextResponse.json({
    releases: placeholderReleases,
    source: 'static',
  });
}
