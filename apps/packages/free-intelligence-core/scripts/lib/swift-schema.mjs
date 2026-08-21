/**
 * Traducción compartida de JSON Schema a Swift. La usan los dos generadores
 * (eventos del stream y registro de conversación) para que la forma del Swift
 * generado no dependa de cuál script lo emitió.
 */
const RESERVADAS = new Set([
  'guard', 'class', 'default', 'return', 'case', 'enum', 'struct', 'protocol',
  'where', 'in', 'for', 'if', 'else', 'let', 'var', 'func', 'init', 'self',
  'switch', 'while', 'repeat', 'do', 'try', 'catch', 'throw', 'as', 'is',
  'nil', 'true', 'false', 'operator', 'extension', 'import', 'internal',
  'private', 'public', 'static', 'subscript', 'typealias', 'associatedtype',
]);

export const mayus = (s) => s.charAt(0).toUpperCase() + s.slice(1);
export const crudo = (s) => s.split('_').map((p, i) => (i ? mayus(p) : p)).join('');
/** El schema tiene campos como `guard`; sin escapar, el Swift no compila. */
export const camel = (s) => (RESERVADAS.has(crudo(s)) ? `\`${crudo(s)}\`` : crudo(s));

export function tipoDe(prop, nombreDef, llave) {
  if (prop.anyOf) {
    const real = prop.anyOf.find((p) => p.type !== 'null');
    return { swift: tipoDe(real ?? {}, nombreDef, llave).swift, opcional: true };
  }
  if (prop.$ref) return { swift: prop.$ref.split('/').pop(), opcional: false };
  if (prop.enum) {
    return { swift: `${nombreDef}${mayus(crudo(llave))}`, opcional: false, enumValores: prop.enum };
  }
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

/** Emite un `struct` Codable con sus CodingKeys y los enums que necesite. */
export function structDe(nombre, def, enumsAcumulados) {
  const requeridos = new Set(def.required ?? []);
  const campos = [];
  const llaves = [];
  for (const [llave, prop] of Object.entries(def.properties ?? {})) {
    const t = tipoDe(prop, nombre, llave);
    if (t.enumValores) {
      enumsAcumulados.set(
        t.swift,
        `enum ${t.swift}: String, Codable {\n` +
          t.enumValores.map((v) => `    case ${camel(v)} = "${v}"`).join('\n') +
          `\n}`
      );
    }
    const opcional = t.opcional || !requeridos.has(llave);
    const doc = prop.description ? `    /// ${prop.description}\n` : '';
    campos.push(`${doc}    var ${camel(llave)}: ${t.swift}${opcional ? '?' : ''}`);
    llaves.push(camel(llave) !== llave ? `        case ${camel(llave)} = "${llave}"` : `        case ${llave}`);
  }
  const doc = def.description ? `/// ${def.description}\n` : '';
  const propias = Object.keys(def.properties ?? {}).map((k) => `"${k}"`).join(', ');
  // El contrato CRECE, y el teléfono se actualiza más lento que la web: un
  // campo que este build no conoce se arrastra intacto en vez de borrarse al
  // volver a guardar. Así se perdieron las imágenes la primera vez.
  const requeridosSet = new Set(def.required ?? []);
  const params = Object.entries(def.properties ?? {}).map(([llave, prop]) => {
    const t = tipoDe(prop, nombre, llave);
    const opcional = t.opcional || !requeridosSet.has(llave);
    return `${camel(llave)}: ${t.swift}${opcional ? '? = nil' : ''}`;
  });
  const asignaciones = Object.keys(def.properties ?? {}).map(
    (llave) => `        self.${camel(llave)} = ${camel(llave)}`
  );
  const memberwise = params.length
    ? `
    init(${params.join(', ')}) {
${asignaciones.join('\n')}
    }
`
    : '';
  const passthrough = `${memberwise}
    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = [${propias}]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
${Object.entries(def.properties ?? {}).map(([llave, prop]) => {
  const t = tipoDe(prop, nombre, llave);
  const opcional = t.opcional || !new Set(def.required ?? []).has(llave);
  return `        ${camel(llave)} = try c.decode${opcional ? 'IfPresent' : ''}(${t.swift}.self, forKey: LlaveLibre(stringValue: "${llave}"))`;
}).join('\n')}
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
${Object.entries(def.properties ?? {}).map(([llave, prop]) => {
  const t = tipoDe(prop, nombre, llave);
  const opcional = t.opcional || !new Set(def.required ?? []).has(llave);
  return `        try c.encode${opcional ? 'IfPresent' : ''}(${camel(llave)}, forKey: LlaveLibre(stringValue: "${llave}"))`;
}).join('\n')}
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
`;
  return `${doc}struct ${nombre}: Codable {\n${campos.join('\n')}\n${passthrough}}`;
}

/** `--check` compartido: falla si el archivo generado quedó viejo. */
export async function escribirOVerificar(salida, ruta, { readFile, writeFile, mkdir }, dirname) {
  if (process.argv.includes('--check')) {
    const actual = await readFile(ruta, 'utf8').catch(() => null);
    if (actual !== salida) {
      console.error(`${ruta.split('/').pop()} está VIEJO respecto al contrato.`);
      process.exit(1);
    }
    console.log(`${ruta.split('/').pop()} está al día con el contrato.`);
    return;
  }
  await mkdir(dirname(ruta), { recursive: true });
  await writeFile(ruta, salida, 'utf8');
  console.log(`escrito ${ruta.split('/').slice(-2).join('/')}`);
}
