/**
 * Generates the TypeScript wire types from the fi-runner event contract.
 *
 * The SSOT lives in the FRAMEWORK, not here:
 *   apps/packages/fi-runner/contracts/agent-events.schema.json
 *   ← generated from apps/packages/fi-runner/fi_runner/events.py
 *
 * This script only translates it. Never hand-edit src/agent/wire.generated.ts —
 * change events.py, regenerate the schema, then run `pnpm gen:events`.
 *
 * A fi-runner test (TestCommittedSchemaIsFresh) guarantees the schema file is
 * never stale relative to the Python models, so this codegen always reads truth.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'json-schema-to-typescript';

const here = dirname(fileURLToPath(import.meta.url));
const SCHEMA = resolve(here, '../../fi-runner/contracts/agent-events.schema.json');
const OUT = resolve(here, '../src/agent/wire.generated.ts');

const BANNER = `/* eslint-disable */
/**
 * DO NOT EDIT — generated from the fi-runner event contract.
 *
 * Source of truth: apps/packages/fi-runner/fi_runner/events.py
 * Schema:          apps/packages/fi-runner/contracts/agent-events.schema.json
 * Regenerate:      pnpm --filter @free-intelligence/core gen:events
 *
 * These are the RAW WIRE frames as fi-runner emits them (snake_case, three
 * envelope shapes). They are NOT the core AgentStreamEvent — that one is the
 * normalized, camelCase contract the reducer consumes. The translation between
 * them lives in the consumer's mapEvent, and now it maps FROM a typed wire
 * frame instead of from \`Record<string, unknown>\` guesswork.
 */
`;

const schema = JSON.parse(await readFile(SCHEMA, 'utf8'));

const ts = await compile(schema, 'AgentWireEvent', {
  bannerComment: '',
  additionalProperties: false,
  style: { singleQuote: true, semi: true },
});

await writeFile(OUT, BANNER + ts, 'utf8');
console.log(`✅ wire types generated → src/agent/wire.generated.ts`);
console.log(`   from ${SCHEMA.split('/free-intelligence/')[1]}`);
