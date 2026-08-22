/**
 * Candado de la capa de CONSUMER: `globals.css` de og118 no puede re-teñir el
 * preset sin decirlo en el contrato.
 *
 * El preset de fi-glass tiene su propio candado (check:glass-css). Éste cuida la
 * otra mitad: lo que og118 pinta ENCIMA. Sin él, alguien re-tiñe una variable en
 * globals.css, la web cambia, y la app nativa —que compone preset + esta capa—
 * se queda con el valor viejo sin que nada avise. Exactamente lo que pasó con el
 * resplandor: la web esmeralda, el teléfono cyan, meses.
 *
 * og118 es el CANARIO de fi-glass: sus overrides describen a un consumer, no al
 * framework, y por eso viven en `consumers.og118` y no en el preset.
 */
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarContrato, colorCss } from './lib/theme-tokens.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const CSS = resolve(here, '../../../og118/web/app/globals.css');

const contrato = await cargarContrato();
const overrides = contrato.consumers?.og118?.colors ?? {};
const css = await readFile(CSS, 'utf8');

/** Resuelve `var(--x)` una vez: globals.css encadena --glass-chat-bg-from -> --og-bg-deep. */
function declarado(nombre) {
  const directo = css.match(new RegExp(`^\\s*${nombre}:\\s*([^;]+);`, 'm'));
  if (!directo) return null;
  const valor = directo[1].trim();
  const indirecto = valor.match(/^var\(\s*(--[\w-]+)/);
  return indirecto ? declarado(indirecto[1]) : valor;
}

const problemas = [];
for (const [nombre, def] of Object.entries(overrides)) {
  const variable = def.cssVar;
  if (!variable) {
    problemas.push(`consumers.og118.${nombre}: falta cssVar en el contrato`);
    continue;
  }
  const real = declarado(variable);
  if (real === null) {
    problemas.push(`${variable}: NO declarada en globals.css (contrato: ${colorCss(def)})`);
    continue;
  }
  const esperado = colorCss(def);
  const norm = (v) => v.toLowerCase().replace(/\s+/g, '');
  if (norm(real) !== norm(esperado)) {
    problemas.push(`${variable}: globals.css dice ${real} · el contrato dice ${esperado}`);
  }
}

if (problemas.length) {
  console.error('La capa consumers.og118 DIVERGE de globals.css:');
  for (const p of problemas) console.error(`  ${p}`);
  console.error('El teléfono compone preset + esta capa: si divergen, pinta distinto que la web.');
  process.exit(1);
}
console.log(`globals.css está al día con consumers.og118 (${Object.keys(overrides).length} overrides).`);
