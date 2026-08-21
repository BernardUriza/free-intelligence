/**
 * Generates the SWIFT wire types from the fi-runner event contract.
 *
 * Same SSOT, same chain, one more consumer:
 *   apps/packages/fi-runner/fi_runner/events.py
 *     -> apps/packages/fi-runner/contracts/agent-events.schema.json
 *          -> src/agent/wire.generated.ts        (pnpm gen:events)
 *          -> og118-ios .../WireEvent.generated.swift  (this script)
 *
 * A native consumer cannot IMPORT the framework, but the contract is DATA, not
 * code — so it must not be transcribed by hand. It was, and every transcription
 * error shipped: `author` typed as String instead of the canonical object made
 * every web conversation render EMPTY on the phone.
 *
 * Never hand-edit the generated file — change events.py, regenerate the schema,
 * run this.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const SCHEMA = resolve(here, '../../fi-runner/contracts/agent-events.schema.json');
const OUT = resolve(here, '../../../og118-ios/Sources/Services/Generated/WireEvent.generated.swift');

const mayus = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const RESERVADAS = new Set([
  'guard', 'class', 'default', 'return', 'case', 'enum', 'struct', 'protocol',
  'where', 'in', 'for', 'if', 'else', 'let', 'var', 'func', 'init', 'self',
  'switch', 'while', 'repeat', 'do', 'try', 'catch', 'throw', 'as', 'is',
  'nil', 'true', 'false', 'operator', 'extension', 'import', 'internal',
  'private', 'public', 'static', 'subscript', 'typealias', 'associatedtype',
]);
const crudo = (s) => s.split('_').map((p, i) => (i ? mayus(p) : p)).join('');
/** El schema tiene un campo `guard`; sin escapar, el Swift generado no compila. */
const camel = (s) => (RESERVADAS.has(crudo(s)) ? `\`${crudo(s)}\`` : crudo(s));
/** `step_done` -> `stepDone`, para el nombre del case. */
const caseName = (s) => crudo(s);

function tipoDe(prop, nombreDef, llave) {
  // `anyOf [X, null]` es como el schema expresa opcional.
  if (prop.anyOf) {
    const real = prop.anyOf.find((p) => p.type !== 'null');
    return { swift: tipoDe(real ?? {}, nombreDef, llave).swift, opcional: true };
  }
  if (prop.$ref) return { swift: prop.$ref.split('/').pop(), opcional: false };
  if (prop.enum) return { swift: `${nombreDef}${mayus(crudo(llave))}`, opcional: false, enumValores: prop.enum };
  switch (prop.type) {
    case 'string': return { swift: 'String', opcional: false };
    case 'integer': return { swift: 'Int', opcional: false };
    case 'number': return { swift: 'Double', opcional: false };
    case 'boolean': return { swift: 'Bool', opcional: false };
    case 'array': {
      const item = tipoDe(prop.items ?? { type: 'string' }, nombreDef, llave);
      return { swift: `[${item.swift}]`, opcional: false };
    }
    default: return { swift: 'JSONValor', opcional: false };
  }
}

const schema = JSON.parse(await readFile(SCHEMA, 'utf8'));
const defs = schema.$defs ?? schema.definitions ?? {};
const mapping = schema.discriminator?.mapping ?? {};
const eventos = new Set(Object.values(mapping).map((r) => r.split('/').pop()));

let cuerpo = '';
const enumsAuxiliares = [];

// Los payloads (todo lo que NO es un evento raíz) se vuelven structs.
for (const [nombre, def] of Object.entries(defs)) {
  if (eventos.has(nombre) || def.type !== 'object') continue;
  const requeridos = new Set(def.required ?? []);
  const campos = [];
  const llaves = [];
  for (const [llave, prop] of Object.entries(def.properties ?? {})) {
    const t = tipoDe(prop, nombre, llave);
    if (t.enumValores) {
      enumsAuxiliares.push(
        `enum ${t.swift}: String, Codable {\n` +
        t.enumValores.map((v) => `    case ${camel(v)} = "${v}"`).join('\n') +
        `\n}`
      );
    }
    const opcional = t.opcional || !requeridos.has(llave);
    campos.push(`    let ${camel(llave)}: ${t.swift}${opcional ? '?' : ''}`);
    if (camel(llave) !== llave) llaves.push(`        case ${camel(llave)} = "${llave}"`);
    else llaves.push(`        case ${llave}`);
  }
  cuerpo += `${def.description ? `/// ${def.description.split('\n')[0]}\n` : ''}struct ${nombre}: Decodable {\n${campos.join('\n')}\n\n    enum CodingKeys: String, CodingKey {\n${llaves.join('\n')}\n    }\n}\n\n`;
}

// La unión discriminada: un case por `type`, con su payload.
const casos = [];
const ramas = [];
for (const [tipo, ref] of Object.entries(mapping)) {
  const nombre = ref.split('/').pop();
  const def = defs[nombre] ?? {};
  const props = Object.entries(def.properties ?? {}).filter(([k]) => k !== 'type');
  const requeridos = new Set(def.required ?? []);
  if (props.length === 0) {
    casos.push(`    case ${caseName(tipo)}`);
    ramas.push(`        case "${tipo}": self = .${caseName(tipo)}`);
    continue;
  }
  const [llave, prop] = props[0];
  const t = tipoDe(prop, nombre, llave);
  const opcional = t.opcional || !requeridos.has(llave);
  casos.push(`    case ${caseName(tipo)}(${camel(llave)}: ${t.swift}${opcional ? '?' : ''})`);
  ramas.push(
    `        case "${tipo}":\n` +
    `            self = .${caseName(tipo)}(${camel(llave)}: try c.decode${opcional ? 'IfPresent' : ''}(${t.swift}.self, forKey: .${camel(llave)}))`
  );
}

const todasLasLlaves = new Set(['type']);
for (const [, ref] of Object.entries(mapping)) {
  const def = defs[ref.split('/').pop()] ?? {};
  for (const k of Object.keys(def.properties ?? {})) todasLasLlaves.add(k);
}

const salida = `// DO NOT EDIT — generado desde el contrato de eventos de fi-runner.
//
//   apps/packages/fi-runner/fi_runner/events.py
//     -> apps/packages/fi-runner/contracts/agent-events.schema.json
//       -> este archivo   (pnpm --filter @free-intelligence/core gen:swift-events)
//
// Un consumer nativo no puede IMPORTAR el framework, pero el contrato es DATO,
// no código: transcribirlo a mano es lo que hizo que \`author\` se tipara como
// String y TODA conversación de la web se viera vacía en el teléfono.

import Foundation

${enumsAuxiliares.join('\n\n')}

${cuerpo}/// Un frame del stream, tal como el contrato lo declara.
enum WireEvent: Decodable {
${casos.join('\n')}
    /// Un \`type\` que este build no conoce. NO se descarta: el consumer decide
    /// qué hacer con él, pero nunca desaparece en silencio.
    case desconocido(String)

    private enum CodingKeys: String, CodingKey {
${[...todasLasLlaves].map((k) => (camel(k) !== k ? `        case ${camel(k)} = "${k}"` : `        case ${k}`)).join('\n')}
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let tipo = try c.decode(String.self, forKey: .type)
        switch tipo {
${ramas.join('\n')}
        default: self = .desconocido(tipo)
        }
    }
}
`;

// `--check` no escribe: falla si el generado está viejo respecto al contrato.
// Sin esto, el archivo se pudre en silencio y volvemos a tener una copia a mano
// con pasos extra — que es justo lo que este generador vino a matar.
if (process.argv.includes('--check')) {
  const actual = await readFile(OUT, 'utf8').catch(() => null);
  if (actual !== salida) {
    console.error('WireEvent.generated.swift está VIEJO respecto al contrato.');
    console.error('Corre: pnpm --filter @free-intelligence/core gen:swift-events');
    process.exit(1);
  }
  console.log('WireEvent.generated.swift está al día con el contrato.');
  process.exit(0);
}

await mkdir(dirname(OUT), { recursive: true });
await writeFile(OUT, salida, 'utf8');
console.log(`escrito ${OUT.split('/').slice(-2).join('/')} — ${Object.keys(mapping).length} eventos, ${Object.keys(defs).length - eventos.size} payloads`);
