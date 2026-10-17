/**
 * Genera el módulo TypeScript de copy que consume core, desde el contrato.
 *
 *   contracts/copy.json                 <- LA FUENTE (escrita a mano)
 *     -> src/copy.generated.ts          (este script)
 *     -> og118-ios/.../Copy.generated.swift   (gen:swift-copy)
 *
 * El aviso de `deferred` se copió a mano a Swift el mismo día que nació en
 * core; una frase que vive dos veces diverge en cuanto alguien la retoca.
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarCopy } from './lib/copy.mjs';
import { escribirOVerificar } from './lib/swift-schema.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../src/copy.generated.ts');

const entradas = await cargarCopy();
const literal = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;

const lineas = [];
for (const e of entradas) {
  if (e.descripcion) lineas.push(`  /** ${e.descripcion} */`);
  if (e.params.length === 0) {
    lineas.push(`  ${e.nombre}: ${literal(e.texto)},`);
  } else {
    const firma = e.params.map((p) => `${p}: string`).join(', ');
    let cuerpo = literal(e.texto);
    for (const p of e.params) cuerpo = `${cuerpo}.split('{${p}}').join(${p})`;
    lineas.push(`  ${e.nombre}: (${firma}): string => ${cuerpo},`);
  }
}

const salida = `// DO NOT EDIT — generado desde contracts/copy.json (pnpm gen:copy).
//
// Las frases que el substrato posee. Swift deriva del mismo contrato
// (Copy.generated.swift); ninguna superficie manda sobre la otra.

export const COPY = {
${lineas.join('\n')}
} as const;
`;

await escribirOVerificar(salida, OUT, { readFile, writeFile, mkdir }, dirname);
