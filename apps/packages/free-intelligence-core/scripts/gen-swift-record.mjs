/**
 * Genera el Swift del registro de conversación desde el contrato.
 *
 *   contracts/conversation-record.schema.json   <- LA FUENTE (escrita a mano)
 *     -> og118-ios/.../ConversationRecord.generated.swift   (este script)
 *     -> src/chat/record.generated.ts                       (gen:record-types)
 *
 * Ningún lenguaje manda sobre los otros: los tres derivan del mismo schema.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { structDe, escribirOVerificar } from './lib/swift-schema.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const SCHEMA = resolve(here, '../contracts/conversation-record.schema.json');
const OUT = resolve(here, '../../../og118-ios/Sources/Services/Generated/ConversationRecord.generated.swift');

const schema = JSON.parse(await readFile(SCHEMA, 'utf8'));
const defs = schema.$defs ?? {};
const enums = new Map();
const structs = [];

for (const [nombre, def] of Object.entries(defs)) {
  structs.push(structDe(nombre, def, enums));
}
structs.push(structDe(schema.title, schema, enums));

const salida = `// DO NOT EDIT — generado desde contracts/conversation-record.schema.json
//
// El schema es LA FUENTE, escrita a mano. TypeScript, Swift y el modelo del
// servidor derivan de él; ninguno manda sobre los otros. Un contrato que vive
// como tipos de UN lenguaje obliga a los demás a transcribirlo, y cada
// transcripción diverge — así se perdieron las imágenes y así se vaciaron los
// hilos de la web en el teléfono.
//
//   pnpm --filter @free-intelligence/core gen:swift-record
//   pnpm --filter @free-intelligence/core check:swift-record

import Foundation

${[...enums.values()].join('\n\n')}

${structs.join('\n\n')}
`;

await escribirOVerificar(salida, OUT, { readFile, writeFile, mkdir }, dirname);
