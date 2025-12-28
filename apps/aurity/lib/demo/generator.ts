/**
 * Free Intelligence - Deterministic Dataset Generator
 *
 * Generates reproducible demo sessions/events using seedable PRNG.
 *
 * File: lib/demo/generator.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 *
 * Philosophy AURITY:
 * - Same seed → same IDs, timestamps, content
 * - Realistic distributions (mix = 80% small + 20% large)
 * - Medical-style corpus (no PHI, synthetic only)
 */

import { PRNG } from './prng';
import {
  DemoConfig,
  DemoManifest,
  EventKind,
  SpeakerTemplate,
  TextCorpus,
} from './types';
import { SessionSummary, SessionDetail, EventResponse } from '@aurity-standalone/api-client/timeline';

/**
 * Text corpus for demo events (medical terminology, synthetic)
 */
const TEXT_CORPUS: TextCorpus = {
  symptoms: [
    'Persistent headache for 3 days',
    'Fever 38.5°C, started yesterday',
    'Abdominal pain, lower right quadrant',
    'Shortness of breath on exertion',
    'Fatigue and dizziness',
    'Chest tightness, radiating to left arm',
    'Nausea and vomiting',
    'Joint pain, bilateral knees',
    'Visual disturbances, flashing lights',
    'Persistent dry cough',
  ],
  diagnoses: [
    'Tension headache, rule out migraine',
    'Viral upper respiratory infection',
    'Acute appendicitis, surgical consult',
    'Possible cardiac angina, EKG ordered',
    'Dehydration with orthostatic hypotension',
    'Gastroenteritis, likely viral',
    'Osteoarthritis, bilateral knees',
    'Migraine with aura',
    'Acute bronchitis',
    'Essential hypertension',
  ],
  treatments: [
    'Ibuprofen 400mg PO q6h PRN',
    'Rest, hydration, acetaminophen',
    'NPO, IV fluids, surgical prep',
    'Nitroglycerin 0.4mg SL PRN',
    'NS 1L IV bolus, oral rehydration',
    'Ondansetron 4mg IV, clear liquids',
    'Physical therapy referral',
    'Sumatriptan 50mg PO',
    'Azithromycin 500mg daily x5 days',
    'Lisinopril 10mg PO daily',
  ],
  questions: [
    'When did symptoms start?',
    'Any allergies to medications?',
    'Previous history of similar episodes?',
    'Current medications?',
    'Pain scale 1-10?',
    'Any recent travel?',
    'Family history of cardiac disease?',
    'Duration of symptoms?',
    'Associated symptoms?',
    'Recent exposures to illness?',
  ],
  responses: [
    'Started 3 days ago, gradually worsening',
    'No known drug allergies',
    'First time experiencing this',
    'Taking lisinopril for hypertension',
    'Pain is 7/10, constant',
    'No recent travel',
    'Father had MI at age 55',
    'Symptoms persist for 2-3 hours',
    'Also feeling fatigued',
    'Exposed to sick coworker last week',
  ],
};

/**
 * Speaker templates
 */
const SPEAKERS: SpeakerTemplate[] = [
  { role: 'doctor', name: 'Dr. García' },
  { role: 'doctor', name: 'Dr. Mendoza' },
  { role: 'patient', name: 'Patient A' },
  { role: 'patient', name: 'Patient B' },
  { role: 'nurse', name: 'Nurse López' },
  { role: 'system', name: 'FI System' },
];

/**
 * Event kinds with weights
 */
const EVENT_KINDS: EventKind[] = [
  'ASR_TRANSCRIBED',
  'LLM_RESPONSE_GENERATED',
  'DECISION_APPLIED',
  'REDACTION_APPLIED',
  'POLICY_EVALUATED',
];

/**
 * Generate deterministic session ID
 */
function generateSessionId(prng: PRNG, index: number): string {
  // Deterministic: hash(seed + "session:" + index)
  const sessionSeed = `${prng.getSeed()}:session:${index}`;
  const tempPrng = new PRNG(sessionSeed);
  return tempPrng.uuid('ses-');
}

/**
 * Generate event count for session based on profile
 */
function getEventCount(
  prng: PRNG,
  profile: 'small' | 'large' | 'mix',
  sessionIndex: number,
  _totalSessions: number
): number {
  if (profile === 'small') {
    return prng.int(30, 80);
  }
  if (profile === 'large') {
    return prng.int(400, 2000);
  }

  // Mix: 80% small, 20% large
  // Ensure at least 1 large session
  const isLarge =
    sessionIndex === 0 || // First session always large for virtualization test
    prng.next() < 0.2; // 20% chance

  return isLarge ? prng.int(400, 2000) : prng.int(30, 80);
}

/**
 * Generate session summary
 */
export function generateSessionSummary(
  prng: PRNG,
  config: DemoConfig,
  index: number
): SessionSummary {
  const sessionId = generateSessionId(prng, index);
  const eventCount = getEventCount(prng, config.eventsProfile, index, config.sessions);

  // Timestamps: sessions spaced 1-7 days apart
  const daysAgo = index * prng.int(1, 7);
  const startDate = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000);
  const durationMs = prng.int(300000, 7200000); // 5min - 2h
  const endDate = new Date(startDate.getTime() + durationMs);

  // Speakers (used for demo session metadata)
  prng.pick(SPEAKERS.filter((s) => s.role === 'doctor'));
  prng.pick(SPEAKERS.filter((s) => s.role === 'patient'));

  // Tokens (based on event count) - only tokensIn used for stats
  const avgTokensPerEvent = prng.int(50, 150);
  const totalTokens = eventCount * avgTokensPerEvent;
  const _tokensIn = Math.floor(totalTokens * 0.6);

  // Preview (first symptom + diagnosis)
  const symptom = prng.pick(TEXT_CORPUS.symptoms);
  const diagnosis = prng.pick(TEXT_CORPUS.diagnoses);
  const preview = `${symptom.substring(0, 60)}... → ${diagnosis.substring(0, 60)}...`;

  return {
    metadata: {
      session_id: sessionId,
      thread_id: prng.next() > 0.7 ? prng.uuid('thr-') : null,
      owner_hash: `owner_${prng.int(1000, 9999)}`,
      created_at: startDate.toISOString(),
      updated_at: endDate.toISOString(),
    },
    timespan: {
      start: startDate.toISOString(),
      end: endDate.toISOString(),
      duration_ms: durationMs,
      duration_human: `${Math.floor(durationMs / 60000)}m ${Math.floor((durationMs % 60000) / 1000)}s`,
    },
    size: {
      interaction_count: eventCount,
      total_tokens: totalTokens,
      total_chars: totalTokens * 4, // Approx 4 chars/token
      avg_tokens_per_interaction: avgTokensPerEvent,
      size_human: eventCount > 200 ? 'LARGE' : 'SMALL',
    },
    policy_badges: {
      hash_verified: 'OK',
      policy_compliant: 'OK',
      redaction_applied: prng.next() > 0.3 ? 'OK' : 'N/A',
      audit_logged: 'OK',
    },
    preview,
  };
}

/**
 * Generate event for session
 */
function generateEvent(
  prng: PRNG,
  sessionId: string,
  eventIndex: number,
  baseTimestamp: Date
): EventResponse {
  const eventId = `evt-${sessionId.split('-')[1]}-${eventIndex.toString().padStart(4, '0')}`;
  const kind = prng.pick(EVENT_KINDS);

  // Timestamp: events spaced 10-300 seconds apart
  const offsetMs = eventIndex * prng.int(10000, 300000);
  const timestamp = new Date(baseTimestamp.getTime() + offsetMs);

  // Who (actor)
  const speaker = prng.pick(SPEAKERS);
  const who = speaker.name;

  // What (text content based on kind)
  let what = '';
  let summary = null;

  switch (kind) {
    case 'ASR_TRANSCRIBED':
      what = prng.pick([...TEXT_CORPUS.symptoms, ...TEXT_CORPUS.questions, ...TEXT_CORPUS.responses]);
      summary = `Transcribed: ${what.substring(0, 40)}...`;
      break;
    case 'LLM_RESPONSE_GENERATED':
      what = prng.pick([...TEXT_CORPUS.diagnoses, ...TEXT_CORPUS.treatments]);
      summary = `LLM: ${what.substring(0, 40)}...`;
      break;
    case 'DECISION_APPLIED':
      what = `Decision: ${prng.pick(['TRIAGE_RED', 'TRIAGE_YELLOW', 'TRIAGE_GREEN'])}`;
      summary = what;
      break;
    case 'REDACTION_APPLIED':
      what = 'Redaction applied to sensitive content';
      summary = 'Content redacted';
      break;
    case 'POLICY_EVALUATED':
      what = `Policy check: ${prng.pick(['PHI_SCAN', 'AUDIT_LOG', 'EXPORT_MANIFEST'])}`;
      summary = what;
      break;
  }

  return {
    event_id: eventId,
    event_type: kind,
    timestamp: timestamp.toISOString(),
    who,
    what,
    summary,
    content_hash: `hash_${prng.int(10000000, 99999999).toString(16)}`,
    redaction_policy: prng.next() > 0.7 ? 'REDACT_PHI' : 'NONE',
    causality: [],
    tags: prng.shuffle(['medical', 'demo', 'synthetic']).slice(0, prng.int(1, 3)),
    auto_generated: prng.next() > 0.2,
    generation_mode: prng.pick(['auto', 'manual', 'hybrid']),
    confidence_score: parseFloat((0.7 + prng.next() * 0.3).toFixed(2)),
  };
}

/**
 * Generate session detail with events
 */
export function generateSessionDetail(
  prng: PRNG,
  summary: SessionSummary
): SessionDetail {
  const eventCount = summary.size.interaction_count;
  const events: EventResponse[] = [];

  const baseTimestamp = new Date(summary.timespan.start);

  for (let i = 0; i < eventCount; i++) {
    events.push(generateEvent(prng, summary.metadata.session_id, i, baseTimestamp));
  }

  const autoEvents = events.filter((e) => e.auto_generated).length;
  const manualEvents = eventCount - autoEvents;

  const redactionStats: Record<string, number> = {};
  events.forEach((e) => {
    redactionStats[e.redaction_policy] = (redactionStats[e.redaction_policy] || 0) + 1;
  });

  return {
    ...summary,
    events,
    generation_mode: 'hybrid',
    auto_events_count: autoEvents,
    manual_events_count: manualEvents,
    redaction_stats: redactionStats,
  };
}

/**
 * Generate demo manifest (trazabilidad)
 */
export function generateManifest(
  config: DemoConfig,
  sessionIds: string[]
): DemoManifest {
  // Compute digest of all session IDs
  const idsConcat = sessionIds.join('');
  let hash = 0;
  for (let i = 0; i < idsConcat.length; i++) {
    const char = idsConcat.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  const idsDigest = Math.abs(hash).toString(16).substring(0, 8);

  return {
    version: '1.0',
    seed: config.seed,
    sessions: config.sessions,
    profile: config.eventsProfile,
    latency: `${config.latencyMs.min}-${config.latencyMs.max}`,
    error_rate: config.errorRatePct,
    ids_digest: idsDigest,
    generatedAt: new Date().toISOString(),
  };
}

/**
 * Generate complete dataset
 */
export function generateDemoDataset(config: DemoConfig): {
  summaries: SessionSummary[];
  manifest: DemoManifest;
} {
  const prng = new PRNG(config.seed);
  const summaries: SessionSummary[] = [];

  // Generate sessions
  for (let i = 0; i < config.sessions; i++) {
    summaries.push(generateSessionSummary(prng, config, i));
  }

  // Generate manifest
  const sessionIds = summaries.map((s) => s.metadata.session_id);
  const manifest = generateManifest(config, sessionIds);

  return { summaries, manifest };
}
