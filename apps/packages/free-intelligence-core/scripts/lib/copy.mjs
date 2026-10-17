import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
export const CONTRATO = resolve(here, '../../contracts/copy.json');

/** `turn.deferredNotice` -> `turnDeferredNotice`. */
export const nombre = (clave) =>
  clave.split('.').map((p, i) => (i ? p.charAt(0).toUpperCase() + p.slice(1) : p)).join('');

export async function cargarCopy() {
  const contrato = JSON.parse(await readFile(CONTRATO, 'utf8'));
  return Object.entries(contrato.strings).map(([clave, def]) => {
    const params = def.params ?? [];
    for (const p of params) {
      if (!def.text.includes(`{${p}}`)) throw new Error(`${clave}: el param {${p}} no aparece en el texto`);
    }
    const huecos = [...def.text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
    for (const h of huecos) {
      if (!params.includes(h)) throw new Error(`${clave}: el hueco {${h}} no está declarado en params`);
    }
    return { clave, nombre: nombre(clave), texto: def.text, params, descripcion: def.description ?? '' };
  });
}
