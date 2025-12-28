/**
 * Free Intelligence - Demo Data Adapter
 *
 * Mirror contract for Timeline API with latency/error injection.
 *
 * File: lib/demo/adapter.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 *
 * Philosophy AURITY:
 * - Demo ≠ maqueta: misma interfaz, mismos límites de rendimiento
 * - Control visible: latencia/errores configurables
 * - Cache determinista: seed invalida y regenera
 */

import { PRNG } from './prng';
import { DemoConfig, DemoManifest } from './types';
import {
  SessionSummary,
  SessionDetail,
  TimelineStats,
} from '@aurity-standalone/api-client/timeline';
import {
  generateDemoDataset,
  generateSessionDetail,
} from './generator';

/**
 * Parse demo config from environment variables
 */
export function parseDemoConfig(): DemoConfig {
  const enabled = process.env.NEXT_PUBLIC_DEMO_MODE === '1';
  const seed = process.env.NEXT_PUBLIC_DEMO_SEED || 'fi-2025';
  const sessions = parseInt(
    process.env.NEXT_PUBLIC_DEMO_SESSIONS || '24',
    10
  );
  const eventsProfile = (process.env.NEXT_PUBLIC_DEMO_EVENTS_PROFILE ||
    'mix') as 'small' | 'large' | 'mix';

  // Parse latency range "80-140"
  const latencyStr = process.env.NEXT_PUBLIC_DEMO_LATENCY_MS || '80-140';
  const [minStr, maxStr] = latencyStr.split('-');
  const latencyMs = {
    min: parseInt(minStr, 10) || 80,
    max: parseInt(maxStr, 10) || 140,
  };

  const errorRatePct = parseInt(
    process.env.NEXT_PUBLIC_DEMO_ERROR_RATE_PCT || '0',
    10
  );

  return {
    enabled,
    seed,
    sessions,
    eventsProfile,
    latencyMs,
    errorRatePct,
  };
}

/**
 * Demo data adapter with caching
 */
export class DemoAdapter {
  private config: DemoConfig;
  private summaries: SessionSummary[] | null = null;
  private manifest: DemoManifest | null = null;
  private prng: PRNG;

  private readonly STORAGE_KEY_SUMMARIES = 'fi_demo_summaries';
  private readonly STORAGE_KEY_MANIFEST = 'fi_demo_manifest';

  constructor(config?: DemoConfig) {
    this.config = config || parseDemoConfig();
    this.prng = new PRNG(this.config.seed);
    this.loadFromCache();
  }

  /**
   * Load cached dataset or generate new one
   */
  private loadFromCache(): void {
    if (typeof window === 'undefined') return; // SSR guard

    try {
      const cachedManifest = localStorage.getItem(this.STORAGE_KEY_MANIFEST);
      if (cachedManifest) {
        const manifest: DemoManifest = JSON.parse(cachedManifest);

        // Check if seed matches (invalidate if different)
        if (manifest.seed === this.config.seed) {
          const cachedSummaries = localStorage.getItem(
            this.STORAGE_KEY_SUMMARIES
          );
          if (cachedSummaries) {
            this.summaries = JSON.parse(cachedSummaries);
            this.manifest = manifest;
            console.info(
              '[DemoAdapter] Loaded cached dataset',
              manifest.ids_digest
            );
            return;
          }
        } else {
          console.info('[DemoAdapter] Seed changed, regenerating dataset');
        }
      }
    } catch (error) {
      console.warn('[DemoAdapter] Failed to load cache:', error);
    }

    // Generate new dataset
    this.regenerateDataset();
  }

  /**
   * Regenerate dataset and save to cache
   */
  private regenerateDataset(): void {
    console.info('[DemoAdapter] Generating dataset...', this.config);

    const startTime = performance.now();
    const { summaries, manifest } = generateDemoDataset(this.config);
    const buildTimeMs = performance.now() - startTime;

    this.summaries = summaries;
    this.manifest = manifest;

    // Save to cache
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(
          this.STORAGE_KEY_SUMMARIES,
          JSON.stringify(summaries)
        );
        localStorage.setItem(
          this.STORAGE_KEY_MANIFEST,
          JSON.stringify(manifest)
        );
      } catch (error) {
        console.warn('[DemoAdapter] Failed to cache dataset:', error);
      }
    }

    // Log metrics
    const totalEvents = summaries.reduce(
      (sum, s) => sum + s.size.interaction_count,
      0
    );
    console.info('[DemoAdapter] Dataset generated', {
      seed: manifest.seed,
      sessions: summaries.length,
      totalEvents,
      buildTimeMs: buildTimeMs.toFixed(0),
      idsDigest: manifest.ids_digest,
    });

    // Track metric (if available)
    if (typeof window !== 'undefined' && (window as any).fiMetrics) {
      (window as any).fiMetrics.track('ui.demo.loaded', {
        seed: manifest.seed,
        sessions: summaries.length,
        events_total: totalEvents,
        ms_build: buildTimeMs,
      });
    }
  }

  /**
   * Inject latency (simulated network delay)
   */
  private async injectLatency(): Promise<void> {
    const delay =
      this.prng.int(this.config.latencyMs.min, this.config.latencyMs.max);
    await new Promise((resolve) => setTimeout(resolve, delay));
  }

  /**
   * Inject error (probabilistic 5xx simulation)
   */
  private shouldInjectError(): boolean {
    if (this.config.errorRatePct === 0) return false;
    return this.prng.next() * 100 < this.config.errorRatePct;
  }

  /**
   * Get session summaries (mirror timeline API)
   */
  async getSessionSummaries(params?: {
    limit?: number;
    offset?: number;
    sort?: 'recent' | 'oldest' | 'events_desc' | 'events_asc';
  }): Promise<SessionSummary[]> {
    await this.injectLatency();

    // Error injection
    if (this.shouldInjectError()) {
      console.warn('[DemoAdapter] Injecting 5xx error');
      if (typeof window !== 'undefined' && (window as any).fiMetrics) {
        (window as any).fiMetrics.track('ui.demo.error_injected.count', 1);
      }
      throw new Error('Simulated 5xx error (demo error injection)');
    }

    if (!this.summaries) {
      throw new Error('Demo dataset not loaded');
    }

    const { limit = 50, offset = 0, sort = 'recent' } = params || {};

    // Sort
    const sorted = [...this.summaries];
    switch (sort) {
      case 'recent':
        sorted.sort(
          (a, b) =>
            new Date(b.metadata.created_at).getTime() -
            new Date(a.metadata.created_at).getTime()
        );
        break;
      case 'oldest':
        sorted.sort(
          (a, b) =>
            new Date(a.metadata.created_at).getTime() -
            new Date(b.metadata.created_at).getTime()
        );
        break;
      case 'events_desc':
        sorted.sort(
          (a, b) => b.size.interaction_count - a.size.interaction_count
        );
        break;
      case 'events_asc':
        sorted.sort(
          (a, b) => a.size.interaction_count - b.size.interaction_count
        );
        break;
    }

    // Paginate
    return sorted.slice(offset, offset + limit);
  }

  /**
   * Get session detail by ID (mirror timeline API)
   */
  async getSessionDetail(sessionId: string): Promise<SessionDetail> {
    await this.injectLatency();

    // Error injection
    if (this.shouldInjectError()) {
      console.warn('[DemoAdapter] Injecting 5xx error');
      if (typeof window !== 'undefined' && (window as any).fiMetrics) {
        (window as any).fiMetrics.track('ui.demo.error_injected.count', 1);
      }
      throw new Error('Simulated 5xx error (demo error injection)');
    }

    if (!this.summaries) {
      throw new Error('Demo dataset not loaded');
    }

    // Find session summary
    const summary = this.summaries.find(
      (s) => s.metadata.session_id === sessionId
    );

    if (!summary) {
      throw new Error(`Session ${sessionId} not found`);
    }

    // Generate detail (with events) deterministically
    // Use session-specific PRNG for reproducibility
    const sessionPrng = new PRNG(`${this.config.seed}:detail:${sessionId}`);
    const detail = generateSessionDetail(sessionPrng, summary);

    return detail;
  }

  /**
   * Get timeline stats (aggregated)
   */
  async getTimelineStats(): Promise<TimelineStats> {
    await this.injectLatency();

    if (!this.summaries) {
      throw new Error('Demo dataset not loaded');
    }

    const totalSessions = this.summaries.length;
    const totalEvents = this.summaries.reduce(
      (sum, s) => sum + s.size.interaction_count,
      0
    );
    const totalTokens = this.summaries.reduce(
      (sum, s) => sum + s.size.total_tokens,
      0
    );

    // Event types breakdown (approximation)
    const eventTypesBreakdown: Record<string, number> = {
      ASR_TRANSCRIBED: Math.floor(totalEvents * 0.3),
      LLM_RESPONSE_GENERATED: Math.floor(totalEvents * 0.25),
      DECISION_APPLIED: Math.floor(totalEvents * 0.15),
      REDACTION_APPLIED: Math.floor(totalEvents * 0.1),
      POLICY_EVALUATED: Math.floor(totalEvents * 0.2),
    };

    // Date range
    const dates = this.summaries.map((s) =>
      new Date(s.metadata.created_at).getTime()
    );
    const minDate = new Date(Math.min(...dates)).toISOString();
    const maxDate = new Date(Math.max(...dates)).toISOString();

    return {
      total_sessions: totalSessions,
      total_events: totalEvents,
      total_tokens: totalTokens,
      avg_events_per_session: Math.floor(totalEvents / totalSessions),
      event_types_breakdown: eventTypesBreakdown,
      redaction_stats: {
        REDACT_PHI: Math.floor(totalEvents * 0.3),
        NONE: Math.floor(totalEvents * 0.7),
      },
      generation_modes: {
        auto: Math.floor(totalEvents * 0.7),
        manual: Math.floor(totalEvents * 0.2),
        hybrid: Math.floor(totalEvents * 0.1),
      },
      date_range: {
        start: minDate,
        end: maxDate,
      },
    };
  }

  /**
   * Get demo manifest (trazabilidad)
   */
  getManifest(): DemoManifest | null {
    return this.manifest;
  }

  /**
   * Get config
   */
  getConfig(): DemoConfig {
    return this.config;
  }

  /**
   * Update config and regenerate dataset
   */
  updateConfig(newConfig: Partial<DemoConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.prng = new PRNG(this.config.seed);
    this.regenerateDataset();
  }

  /**
   * Clear cache and regenerate
   */
  clearCache(): void {
    if (typeof window === 'undefined') return;

    localStorage.removeItem(this.STORAGE_KEY_SUMMARIES);
    localStorage.removeItem(this.STORAGE_KEY_MANIFEST);
    this.regenerateDataset();
  }
}
