/**
 * Genera el Copy nativo de og118-ios desde el contrato de frases.
 *
 *   contracts/copy.json                        <- LA FUENTE (escrita a mano)
 *     -> og118-ios/.../Copy.generated.swift    (este script)
 *     -> src/copy.generated.ts                 (gen:copy)
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarCopy } from './lib/copy.mjs';
import { escribirOVerificar } from './lib/swift-schema.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../../../og118-ios/Sources/Services/Generated/Copy.generated.swift');

const entradas = await cargarCopy();
const literal = (s) => `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;

const lineas = [];
for (const e of entradas) {
  if (e.descripcion) lineas.push(`    /// ${e.descripcion}`);
  if (e.params.length === 0) {
    lineas.push(`    static let ${e.nombre} = ${literal(e.texto)}`);
  } else {
    const firma = e.params.map((p) => `${p}: String`).join(', ');
    let cuerpo = literal(e.texto);
    for (const p of e.params) cuerpo = cuerpo.replaceAll(`{${p}}`, `\\(${p})`);
    lineas.push(`    static func ${e.nombre}(${firma}) -> String {`);
    lineas.push(`        ${cuerpo}`);
    lineas.push('    }');
  }
  lineas.push('');
}
lineas.pop();

const salida = `// DO NOT EDIT — generado desde contracts/copy.json
//
// El contrato es LA FUENTE, escrita a mano. core (copy.generated.ts) y este
// archivo derivan de él; ninguna superficie manda sobre la otra. El aviso de
// \`deferred\` se transcribió a mano el día que nació: así es como una frase
// termina diciendo dos cosas distintas en la web y en el teléfono.
//
//   pnpm --filter @free-intelligence/core gen:swift-copy
//   pnpm --filter @free-intelligence/core check:swift-copy

import Foundation

enum Copy {
${lineas.join('\n')}
}
`;

await escribirOVerificar(salida, OUT, { readFile, writeFile, mkdir }, dirname);
