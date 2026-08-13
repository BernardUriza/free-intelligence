/**
 * Genera los tipos TypeScript del registro de conversación desde el contrato.
 *
 *   contracts/conversation-record.schema.json   <- LA FUENTE (escrita a mano)
 *     -> src/chat/record.generated.ts           (este script)
 *     -> og118-ios/.../ConversationRecord.generated.swift
 *
 * `message.ts` y `record.ts` conservan su documentación y sus helpers, pero
 * dejan de DECLARAR la forma: la importan de aquí. Ningún lenguaje manda.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'json-schema-to-typescript';

const here = dirname(fileURLToPath(import.meta.url));
const SCHEMA = resolve(here, '../contracts/conversation-record.schema.json');
const OUT = resolve(here, '../src/chat/record.generated.ts');

const schema = JSON.parse(await readFile(SCHEMA, 'utf8'));
const ts = await compile(schema, 'ConversationRecord', {
  bannerComment: `/* eslint-disable */
/**
 * DO NOT EDIT — generado desde contracts/conversation-record.schema.json
 *
 * El schema es LA FUENTE. Este archivo, el Swift de og118-ios y el modelo del
 * servidor derivan de él; ninguno manda sobre los otros. Correr:
 *   pnpm --filter @free-intelligence/core gen:record-types
 */`,
  additionalProperties: false,
  declareExternallyReferenced: true,
  style: { singleQuote: true },
});

if (process.argv.includes('--check')) {
  const actual = await readFile(OUT, 'utf8').catch(() => null);
  if (actual !== ts) {
    console.error('record.generated.ts está VIEJO respecto al contrato.');
    process.exit(1);
  }
  console.log('record.generated.ts está al día con el contrato.');
} else {
  await writeFile(OUT, ts, 'utf8');
  console.log('escrito src/chat/record.generated.ts');
}
