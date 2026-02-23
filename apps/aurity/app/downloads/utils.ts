import type { Release } from './types';

/** Detects the user's OS from the user-agent and returns the matching download URL. */
export function getDownloadUrl(release: Release | undefined): string {
  if (!release) return '#';
  if (typeof navigator === 'undefined') return '#';

  const ua = navigator.userAgent.toLowerCase();

  if (ua.includes('mac')) {
    return release.platforms.macos?.url || '#';
  }
  if (ua.includes('win')) {
    return release.platforms.windows?.url || '#';
  }
  if (ua.includes('linux')) {
    return release.platforms.linux?.url || '#';
  }

  // Fallback to Windows
  return release.platforms.windows?.url || '#';
}
