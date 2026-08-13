/**
 * Genera el módulo TypeScript de tokens que consume fi-glass, desde el contrato.
 *
 *   contracts/glass-chat-tokens.json                    <- LA FUENTE (escrita a mano)
 *     -> fi-glass/src/theme/glass-tokens.generated.ts   (este script)
 *     -> og118-ios/.../Theme.generated.swift            (gen:swift-theme)
 *
 * glass-chat-preset.ts y sidebarItemStyle.ts conservan su documentación y su
 * estructura, pero dejan de DECLARAR los valores: los importan de aquí. El CSS
 * estático (glass-chat.css) no puede importar — su candado es check:glass-css.
 *
 * fi-glass shippea su dist/ commiteado: tras regenerar este archivo hay que
 * correr `pnpm --filter fi-glass build` y commitear src y dist juntos.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarContrato, colorCss, medidaCss } from './lib/theme-tokens.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../../fi-glass/src/theme/glass-tokens.generated.ts');

const contrato = await cargarContrato();

const lineas = [];
for (const [nombre, def] of Object.entries(contrato.colors)) {
  if (def.description) lineas.push(`  /** ${def.description} */`);
  lineas.push(`  ${nombre}: '${colorCss(def)}',`);
}
for (const [nombre, def] of Object.entries(contrato.dimensions)) {
  if (def.description) lineas.push(`  /** ${def.description} */`);
  lineas.push(`  ${nombre}: '${medidaCss(def)}',`);
}
for (const [nombre, def] of Object.entries(contrato.css)) {
  if (def.description) lineas.push(`  /** ${def.description} */`);
  lineas.push(`  ${nombre}: '${def.value}',`);
}

const salida = `/* eslint-disable */
/**
 * DO NOT EDIT — generado desde
 * free-intelligence-core/contracts/glass-chat-tokens.json
 *
 * El contrato es LA FUENTE. Este módulo, el Theme de og118-ios y el candado de
 * glass-chat.css derivan de él; ninguna superficie manda sobre las otras.
 *   pnpm --filter @free-intelligence/core gen:theme-tokens
 *   pnpm --filter @free-intelligence/core check:theme-tokens
 */

export const glassTokens = {
${lineas.join('\n')}
} as const;
`;

if (process.argv.includes('--check')) {
  const actual = await readFile(OUT, 'utf8').catch(() => null);
  if (actual !== salida) {
    console.error('glass-tokens.generated.ts está VIEJO respecto al contrato.');
    console.error('Corre: pnpm --filter @free-intelligence/core gen:theme-tokens');
    process.exit(1);
  }
  console.log('glass-tokens.generated.ts está al día con el contrato.');
} else {
  await writeFile(OUT, salida, 'utf8');
  console.log('escrito fi-glass/src/theme/glass-tokens.generated.ts');
}
