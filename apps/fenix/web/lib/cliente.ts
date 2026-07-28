/**
 * El expediente del cliente vive en el TÍTULO de la conversación.
 *
 * No hay base de datos nueva a propósito. La auditoría del 27-jul midió que el
 * 54% de los turnos bloqueados lo estaban por "falta nombre / WhatsApp" — un
 * dato administrativo, no de precio. El equipo ya había adoptado una convención
 * de título («fecha — alumno (escuela) — WhatsApp», 91% de adopción en la
 * segunda semana), así que el dato ya estaba ahí: lo que faltaba era una forma
 * de capturarlo que no fuera pedírselo al modelo turno tras turno.
 *
 * Guardarlo en otra tabla habría creado una segunda verdad que el asistente no
 * lee. El título SÍ lo lee, y viaja con la conversación.
 */

export interface Cliente {
  fecha: string;
  alumno: string;
  escuela: string;
  whatsapp: string;
  completo: boolean;
}

/** Marcadores de "esto todavía no se llenó" vistos en las 33 sesiones reales. */
const HUECO = /^(FALTA\b|<.*>$|\[.*\]$|x{3,}|\d{2}\s*x{4}\s*x{4}$)/i;

function vacio(v: string): boolean {
  const t = v.trim();
  return !t || HUECO.test(t) || /^FALTA/i.test(t);
}

/**
 * `27 jul 1pm — Emma Hernández (4°B) — 33 2388 7997` → sus partes.
 *
 * Tolera los separadores reales encontrados en producción: em dash, dos
 * guiones, guion simple. Un título que no sigue la convención (`tayler
 * material`, `Cotización de lista`) devuelve el título entero como alumno y
 * queda marcado incompleto — que es exactamente lo que es.
 */
export function parseCliente(titulo: string): Cliente {
  const partes = titulo.split(/\s+—\s+|\s+--\s+|\s+–\s+/).map((s) => s.trim());
  const fecha = partes.length > 1 ? partes[0] : '';
  const medio = partes.length > 1 ? partes[1] ?? '' : titulo;
  const cola = partes.slice(2).join(' ');

  const conEscuela = medio.match(/^(.*?)\s*\((.+)\)\s*$/);
  const alumno = (conEscuela ? conEscuela[1] : medio).trim();
  const escuela = (conEscuela ? conEscuela[2] : '').trim();

  const tel = cola.match(/(\d[\d\s]{7,})/);
  const whatsapp = tel ? tel[1].trim() : '';

  return {
    fecha,
    alumno,
    escuela,
    whatsapp,
    completo: !vacio(alumno) && !vacio(whatsapp) && !!fecha,
  };
}

/**
 * fi-core trunca los títulos a 60 caracteres (`TITLE_MAX` en
 * conversation/helpers.ts). La convención que el equipo ya usa pone el WhatsApp
 * AL FINAL — justo donde el corte lo decapita: `…Mendiola 2°) — 33 3448 8256`
 * se guardaba como `…Mendiola 2°) — 33 3448`, perdiendo el dato exacto que este
 * formulario existe para capturar, y sin avisar a nadie.
 *
 * Así que el presupuesto de caracteres se gasta en orden de importancia: fecha,
 * alumno y teléfono son intocables; la ESCUELA es lo que se abrevia hasta que
 * el título quepa. Se conserva la convención del equipo y no se pierde un dígito.
 */
const LARGO_MAX = 60;

export function tituloDeCliente(c: Cliente): string {
  const alumno = c.alumno.trim() || 'FALTA nombre';
  const tel = c.whatsapp.trim() || 'FALTA WhatsApp';
  const fecha =
    c.fecha.trim() || new Date().toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });

  const arma = (escuela: string) =>
    `${fecha} — ${alumno}${escuela ? ` (${escuela})` : ''} — ${tel}`;

  let escuela = c.escuela.trim();
  if (arma(escuela).length <= LARGO_MAX) return arma(escuela);

  const sobra = arma(escuela).length - LARGO_MAX;
  escuela = escuela.length > sobra + 1 ? `${escuela.slice(0, escuela.length - sobra - 1)}…` : '';
  return arma(escuela);
}

/** ¿El nombre del alumno está realmente capturado? */
export function tieneNombre(c: Cliente): boolean {
  return !vacio(c.alumno);
}

/** Qué le falta a este expediente, en palabras que el equipo usa. */
export function faltantes(c: Cliente): string[] {
  const f: string[] = [];
  if (vacio(c.alumno)) f.push('nombre del alumno');
  if (vacio(c.whatsapp)) f.push('WhatsApp');
  if (!c.escuela.trim()) f.push('escuela');
  return f;
}
