/**
 * CapabilityProbe - Detect API availability before activation
 *
 * Probes three critical capabilities:
 * 1. Backend TTS endpoint reachability (OPTIONS request)
 * 2. Audio API support (Web Audio API availability)
 * 3. Autoplay policy (silent audio trick to detect permission)
 *
 * Returns a CapabilityReport with success/failure for each check.
 * Used by AudioPlayerProvider to determine if audio can be activated.
 *
 * Zero-trust principle: Never assume capabilities are available.
 *
 * @module CapabilityProbe
 * @see /apps/aurity/docs/audio/RUNBOOK.md
 */

export interface CapabilityReport {
  backendReachable: boolean;
  audioApiSupported: boolean;
  autoplayAllowed: boolean;
  errors: string[];
  probeTimestamp: number;
}

/**
 * Probe capabilities
 *
 * Performs three async checks:
 * 1. OPTIONS request to backend TTS endpoint
 * 2. Check for Audio and AudioContext APIs
 * 3. Attempt to play silent audio (autoplay detection)
 *
 * @param backendUrl - Backend base URL (e.g., "http://localhost:7001")
 * @returns CapabilityReport with probe results
 */
export async function probeCapabilities(
  backendUrl: string
): Promise<CapabilityReport> {
  const report: CapabilityReport = {
    backendReachable: false,
    audioApiSupported: false,
    autoplayAllowed: false,
    errors: [],
    probeTimestamp: Date.now(),
  };

  // 1. Probe backend TTS endpoint
  try {
    const response = await fetch(`${backendUrl}/api/tts/synthesize`, {
      method: 'OPTIONS', // Preflight request
    });
    // 200 OK or 405 Method Not Allowed are both acceptable
    // (405 means endpoint exists but doesn't support OPTIONS)
    report.backendReachable = response.ok || response.status === 405;
  } catch (error) {
    report.errors.push(`Backend unreachable: ${error}`);
  }

  // 2. Probe Audio API support
  try {
    report.audioApiSupported =
      typeof Audio !== 'undefined' && typeof AudioContext !== 'undefined';
  } catch (error) {
    report.errors.push(`Audio API unsupported: ${error}`);
  }

  // 3. Probe autoplay policy (silent audio trick)
  if (report.audioApiSupported) {
    try {
      const audio = new Audio();
      // Base64-encoded silent WAV file (44 bytes)
      audio.src =
        'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
      await audio.play();
      report.autoplayAllowed = true;
    } catch {
      // Autoplay blocked (expected on first load without user gesture)
      report.autoplayAllowed = false;
    }
  }

  return report;
}

/**
 * Check if audio can be activated
 *
 * Audio requires:
 * - Backend reachable (can generate TTS)
 * - Audio API supported (can play audio)
 *
 * Autoplay permission is NOT required (consent banner handles this).
 *
 * @param report - CapabilityReport from probeCapabilities()
 * @returns True if audio can be activated
 */
export function canActivateAudio(report: CapabilityReport): boolean {
  return report.backendReachable && report.audioApiSupported;
}
