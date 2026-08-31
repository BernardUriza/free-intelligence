'use client';

/**
 * fi-glass · the section surface: Panel, Note, Literal, DataTable.
 *
 * A page made of sections — a clinical form, a settings screen, a report —
 * keeps needing the same four shapes: a glass card with a small uppercase
 * title, a muted side note, a verbatim monospace block, and a bordered table
 * of rows. Every one of them existed in the canary app as bespoke CSS on
 * bare elements; they live here so the NEXT page gets them by import.
 *
 * `Literal` takes `live` because its founding use is a stream: text arriving
 * fragment by fragment that a screen reader should announce as it grows.
 */

import { type ReactNode } from 'react';
import {
  FI_DATA_TABLE_CLASS,
  FI_LITERAL_CLASS,
  FI_LITERAL_INLINE_CLASS,
  FI_NOTE_CLASS,
  FI_NOTE_INLINE_CLASS,
  FI_PANEL_CLASS,
  FI_PANEL_TITLE_CLASS,
  useSurfaceStyle,
} from './surfaceStyle';

function join(base: string, extra?: string): string {
  return extra ? `${base} ${extra}` : base;
}

export interface PanelProps {
  children: ReactNode;
  /** Small uppercase heading, rendered as an <h2>. */
  title?: ReactNode;
  className?: string;
}

export function Panel({ children, title, className }: PanelProps) {
  useSurfaceStyle();
  return (
    <section className={join(FI_PANEL_CLASS, className)}>
      {title ? <h2 className={FI_PANEL_TITLE_CLASS}>{title}</h2> : null}
      {children}
    </section>
  );
}

export interface NoteProps {
  children: ReactNode;
  /** Render as a <span> so the note can live inside a sentence. */
  inline?: boolean;
  className?: string;
}

/** A muted aside: the caveat under a control, the provenance under a figure. */
export function Note({ children, inline = false, className }: NoteProps) {
  useSurfaceStyle();
  if (inline) {
    return <span className={join(FI_NOTE_INLINE_CLASS, className)}>{children}</span>;
  }
  return <p className={join(FI_NOTE_CLASS, className)}>{children}</p>;
}

export interface LiteralProps {
  children: ReactNode;
  /**
   * Announce content changes as they stream in (`aria-live="polite"`).
   * Default: `false` — a static literal should not narrate itself.
   */
  live?: boolean;
  /** Render as a <span> so a verbatim fragment can be quoted mid-sentence. */
  inline?: boolean;
  className?: string;
}

/** Verbatim server-rendered text: a preview, a draft, a quoted source. */
export function Literal({ children, live = false, inline = false, className }: LiteralProps) {
  useSurfaceStyle();
  if (inline) {
    return <span className={join(FI_LITERAL_INLINE_CLASS, className)}>{children}</span>;
  }
  return (
    <pre className={join(FI_LITERAL_CLASS, className)} aria-live={live ? 'polite' : undefined}>
      {children}
    </pre>
  );
}

export interface DataTableRow {
  key: string;
  cells: ReactNode[];
}

export interface DataTableProps {
  /** Column headers; omit for a headerless table. */
  head?: ReactNode[];
  /** Rendered in the given order, always. Empty renders nothing at all. */
  rows: DataTableRow[];
  /** Render each row's first cell as a row header (<th scope="row">). */
  rowHeader?: boolean;
  className?: string;
}

/**
 * A bordered table of rows. Two rules are baked in, same spirit as
 * `CalloutList`: empty renders nothing, and the row order is never touched —
 * the caller ordered those rows deliberately.
 */
export function DataTable({ head, rows, rowHeader = false, className }: DataTableProps) {
  useSurfaceStyle();
  if (!rows.length) return null;
  return (
    <table className={join(FI_DATA_TABLE_CLASS, className)}>
      {head ? (
        <thead>
          <tr>
            {head.map((celda, i) => (
              <th key={i}>{celda}</th>
            ))}
          </tr>
        </thead>
      ) : null}
      <tbody>
        {rows.map((fila) => (
          <tr key={fila.key}>
            {fila.cells.map((celda, i) =>
              rowHeader && i === 0 ? (
                <th scope="row" key={i}>
                  {celda}
                </th>
              ) : (
                <td key={i}>{celda}</td>
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
