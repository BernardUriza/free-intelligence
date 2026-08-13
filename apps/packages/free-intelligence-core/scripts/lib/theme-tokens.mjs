/**
 * Carga y traducción compartida del contrato de tokens de diseño
 * (contracts/glass-chat-tokens.json). La usan los dos generadores y el candado
 * del CSS, para que un color se convierta IGUAL sin importar quién lo emite.
 */
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

export const RUTA_CONTRATO = resolve(here, '../../contracts/glass-chat-tokens.json');

export async function cargarContrato() {
  return JSON.parse(await readFile(RUTA_CONTRATO, 'utf8'));
}

/**
 * Un color del contrato como lo escribe la web: hex a secas si es opaco,
 * `rgba(r, g, b, a)` si trae alpha — el mismo formato byte a byte que
 * glass-chat.css y glass-chat-preset.ts ya usan.
 */
export function colorCss({ hex, alpha }) {
  if (alpha === undefined) return hex;
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 0xff;
  const g = (n >> 8) & 0xff;
  const b = n & 0xff;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Un color del contrato como lo escribe Swift: `Color(hex: 0x...)` + opacity. */
export function colorSwift({ hex, alpha }) {
  const literal = `Color(hex: 0x${hex.slice(1).toUpperCase()})`;
  return alpha === undefined ? literal : `${literal}.opacity(${alpha})`;
}

/** Una medida del contrato como cadena CSS (`16px`, `0.4rem`). */
export function medidaCss(dim) {
  return dim.px !== undefined ? `${dim.px}px` : `${dim.rem}rem`;
}

/**
 * LA REGLA rem→pt, en un solo lugar: 1rem = 16px en la web, y 1px CSS = 1pt
 * en iOS, así que pt = round(rem × 16). Los redondeos que Theme.swift ya
 * traía (0.55rem→9pt, 0.68rem→11pt, 0.85rem→14pt) CAEN de esta regla — no
 * son una tabla aparte que pueda desincronizarse.
 */
export function medidaPt(dim) {
  return dim.px !== undefined ? dim.px : Math.round(dim.rem * 16);
}
