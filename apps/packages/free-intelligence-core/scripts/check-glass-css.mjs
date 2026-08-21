/**
 * Candado del CSS estático contra el contrato de tokens.
 *
 * glass-chat.css no puede importar el módulo generado (es CSS plano, servido
 * desde src/), así que sus custom properties siguen escritas a mano — y este
 * check hace imposible que diverjan en silencio: compara cada declaración
 * `--glass-chat-*` contra el valor que el contrato manda, byte a byte. Se
 * eligió candado y no generación para no destruir los comentarios del CSS,
 * que explican POR QUÉ de cada valor.
 *
 * Sólo se verifican los tokens del contrato; las vars de configuración del
 * consumer (watermark-image/size/position) no son tokens y quedan fuera.
 */
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarContrato, colorCss, medidaCss } from './lib/theme-tokens.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const CSS = resolve(here, '../../fi-glass/src/theme/glass-chat.css');

const contrato = await cargarContrato();
const c = contrato.colors;

const esperado = {
  'accent-from': colorCss(c.accentDeep),
  'accent-to': colorCss(c.accentTo),
  'accent-text': colorCss(c.accentText),
  body: colorCss(c.bgDeep),
  'bg-from': colorCss(c.bgDeep),
  'bg-mid': colorCss(c.bgMid),
  'bg-glow': colorCss(c.glow),
  surface: colorCss(c.surface),
  'surface-border': colorCss(c.surfaceBorder),
  'bubble-user': colorCss(c.bubbleUser),
  'bubble-user-border': colorCss(c.bubbleUserBorder),
  'bubble-assistant': colorCss(c.bubbleAssistant),
  'bubble-border': colorCss(c.bubbleBorder),
  text: colorCss(c.text),
  'text-muted': colorCss(c.textMuted),
  'watermark-opacity': contrato.css.watermarkOpacity.value,
  shadow: contrato.css.shadow.value,
  radius: medidaCss(contrato.dimensions.radius),
};

const css = await readFile(CSS, 'utf8');
const declaradas = new Map();
for (const m of css.matchAll(/--glass-chat-([a-z-]+):\s*([^;]+);/g)) {
  if (!declaradas.has(m[1])) declaradas.set(m[1], m[2].trim());
}

let rojo = false;
for (const [nombre, valor] of Object.entries(esperado)) {
  const real = declaradas.get(nombre);
  if (real === undefined) {
    console.error(`--glass-chat-${nombre}: NO declarada en glass-chat.css (contrato: ${valor})`);
    rojo = true;
  } else if (real !== valor) {
    console.error(`--glass-chat-${nombre}: css dice "${real}", el contrato dice "${valor}"`);
    rojo = true;
  }
}

if (rojo) {
  console.error('glass-chat.css DIVERGE del contrato glass-chat-tokens.json.');
  process.exit(1);
}
console.log(`glass-chat.css está al día con el contrato (${Object.keys(esperado).length} tokens).`);
