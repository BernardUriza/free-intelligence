import { describe, expect, it } from 'vitest';
import { conversationFileName, conversationToMarkdown } from './markdown';
import type { ConversationRecord } from './record';

function record(over: Partial<ConversationRecord> = {}): ConversationRecord {
  return {
    id: 'c1',
    title: 'Fotosíntesis',
    createdAt: '2026-07-28T18:00:00.000Z',
    updatedAt: '2026-07-28T18:05:00.000Z',
    preview: '',
    schemaVersion: 1,
    messages: [
      { id: 'm1', role: 'user', content: '¿Qué es la fotosíntesis?', createdAt: '2026-07-28T18:00:00.000Z' },
      { id: 'm2', role: 'assistant', content: 'Es la cocina de las plantas.', createdAt: '2026-07-28T18:00:10.000Z' },
    ],
    ...over,
  } as unknown as ConversationRecord;
}

describe('conversationToMarkdown', () => {
  it('abre con el título y lleva cada turno con su encabezado', () => {
    const md = conversationToMarkdown(record());
    expect(md).toMatch(/^# Fotosíntesis\n/);
    expect(md).toContain('## Tú\n\n¿Qué es la fotosíntesis?');
    expect(md).toContain('## Asistente\n\nEs la cocina de las plantas.');
  });

  it('respeta las etiquetas y la procedencia que le dé el shell', () => {
    const md = conversationToMarkdown(record(), {
      labels: { assistant: 'Fénix' },
      source: 'Computadoras públicas de Fénix',
    });
    expect(md).toContain('## Fénix');
    expect(md).toContain('*Computadoras públicas de Fénix*');
  });

  it('salta los mensajes vacíos — un turno cancelado no deja un hueco', () => {
    const md = conversationToMarkdown(
      record({
        messages: [
          { id: 'm1', role: 'user', content: 'hola', createdAt: '' },
          { id: 'm2', role: 'assistant', content: '   ', createdAt: '' },
        ] as never,
      }),
    );
    expect(md).toContain('## Tú');
    expect(md).not.toContain('## Asistente');
  });

  it('termina en un solo salto de línea', () => {
    const md = conversationToMarkdown(record());
    expect(md.endsWith('\n')).toBe(true);
    expect(md.endsWith('\n\n')).toBe(false);
  });

  it('sobrevive a una conversación sin mensajes ni título', () => {
    const md = conversationToMarkdown(record({ title: '', messages: [] }));
    expect(md).toContain('# Conversación');
  });
});

describe('conversationFileName', () => {
  it('quita acentos y deja un nombre plano', () => {
    expect(conversationFileName(record())).toBe('Fotosintesis.md');
  });

  it('no deja que un título arme rutas ni rompa la descarga', () => {
    const nombre = conversationFileName(record({ title: 'tarea 3/4: química ¿por qué? 🧪' }));
    expect(nombre).not.toContain('/');
    expect(nombre).not.toContain(':');
    expect(nombre).toMatch(/^[\w-]+\.md$/);
  });

  it('acota el largo y no termina en guion', () => {
    const nombre = conversationFileName(record({ title: 'palabra '.repeat(30) }));
    expect(nombre.length).toBeLessThanOrEqual(64);
    expect(nombre).not.toContain('-.md');
  });

  it('cae en un nombre usable cuando el título no deja nada', () => {
    expect(conversationFileName(record({ title: '¿¡🧪!?' }))).toBe('conversacion.md');
  });
});
