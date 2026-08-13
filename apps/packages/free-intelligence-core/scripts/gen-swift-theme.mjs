/**
 * Genera el Theme nativo de og118-ios desde el contrato de tokens.
 *
 *   contracts/glass-chat-tokens.json              <- LA FUENTE (escrita a mano)
 *     -> og118-ios/.../Theme.generated.swift      (este script)
 *     -> fi-glass/src/theme/glass-tokens.generated.ts   (gen:theme-tokens)
 *
 * Theme.swift era una transcripción a ojo del preset glass-chat — literalmente
 * decía "si la web cambia un token, éste es el archivo que se re-sincroniza".
 * Ese re-sincronizar manual es el mismo hueco que vació los hilos de la web en
 * el iPhone; ahora Theme.swift conserva helpers y composición, y los VALORES
 * salen de aquí.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { escribirOVerificar } from './lib/swift-schema.mjs';
import { cargarContrato, colorSwift, medidaPt } from './lib/theme-tokens.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../../../og118-ios/Sources/Views/Generated/Theme.generated.swift');

const contrato = await cargarContrato();

const colores = Object.entries(contrato.colors).map(([nombre, def]) => {
  const doc = def.description ? `    /// ${def.description}\n` : '';
  return `${doc}    static let ${nombre} = ${colorSwift(def)}`;
});

const medidas = Object.entries(contrato.dimensions).map(([nombre, def]) => {
  const origen = def.px !== undefined ? `${def.px}px` : `${def.rem}rem -> ${medidaPt(def)}pt`;
  const doc = def.description ? `    /// ${def.description} (${origen})\n` : '';
  return `${doc}    static let ${nombre}: CGFloat = ${medidaPt(def)}`;
});

const salida = `// DO NOT EDIT — generado desde contracts/glass-chat-tokens.json
//
// El contrato es LA FUENTE, escrita a mano. El CSS de fi-glass, el mirror
// tipado glassChatPreset y este Theme derivan de él; ninguna superficie manda
// sobre las otras. Un token transcrito a ojo diverge — así se despintó el
// espejo nativo del preset más de una vez.
//
// Regla de conversión: 1rem = 16px en la web y 1px CSS = 1pt en iOS, así que
// pt = round(rem × 16). Los redondeos (0.55rem→9pt, 0.68rem→11pt) caen de la
// regla, no de una tabla aparte.
//
//   pnpm --filter @free-intelligence/core gen:swift-theme
//   pnpm --filter @free-intelligence/core check:swift-theme

import SwiftUI

extension Theme {
${colores.join('\n')}

${medidas.join('\n')}
}
`;

await escribirOVerificar(salida, OUT, { readFile, writeFile, mkdir }, dirname);
