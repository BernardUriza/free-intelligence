/**
 * conversationToMarkdown — la conversación como un archivo que alguien se lleva.
 *
 * Función pura sobre el record: sin React, sin navegador, sin descarga. Quien
 * quiera entregarlo (un Blob en el browser, un archivo en disco, un adjunto de
 * correo) pone ESA parte; aquí sólo vive la forma del documento, que es lo que
 * se repite en cada shell.
 *
 * Markdown y no PDF ni HTML porque el destino real es seguir trabajando: se
 * pega en un cuaderno digital, se abre en cualquier editor, se lee tal cual en
 * texto plano si no hay nada más a la mano.
 */

import type { ChatMessage } from '../chat/message';
import type { ConversationRecord } from './record';

export interface ConversationMarkdownOptions {
  /** Cómo se nombra a cada lado. Default: `Tú` / `Asistente`. */
  labels?: { user?: string; assistant?: string };
  /** Línea de procedencia bajo el título (de dónde salió esta conversación). */
  source?: string;
}

function etiqueta(m: ChatMessage, o: ConversationMarkdownOptions): string {
  if (m.role === 'user') return o.labels?.user ?? 'Tú';
  if (m.role === 'assistant') return o.labels?.assistant ?? 'Asistente';
  return m.role;
}

/** El documento completo, listo para escribir a un archivo `.md`. */
export function conversationToMarkdown(
  record: ConversationRecord,
  options: ConversationMarkdownOptions = {},
): string {
  const partes: string[] = [`# ${record.title || 'Conversación'}`, ''];

  const fecha = record.createdAt || record.updatedAt;
  if (fecha) partes.push(`*${new Date(fecha).toLocaleString()}*`, '');
  if (options.source) partes.push(`*${options.source}*`, '');

  for (const m of record.messages) {
    const contenido = (m.content ?? '').trim();
    if (!contenido) continue;
    partes.push(`## ${etiqueta(m, options)}`, '', contenido, '');
  }

  return `${partes.join('\n').trimEnd()}\n`;
}

/**
 * Un nombre de archivo seguro derivado del título.
 *
 * Los títulos vienen del primer mensaje del usuario, así que traen de todo:
 * `/`, `:`, saltos de línea, emoji. Un nombre sin sanear rompe la descarga en
 * silencio o crea directorios que nadie pidió.
 */
export function conversationFileName(record: ConversationRecord): string {
  const base = (record.title || 'conversacion')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 60)
    .replace(/-+$/, '');
  return `${base || 'conversacion'}.md`;
}
