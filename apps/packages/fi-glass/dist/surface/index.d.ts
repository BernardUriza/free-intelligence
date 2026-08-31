import * as react from 'react';
import { ReactNode } from 'react';

interface PanelProps {
    children: ReactNode;
    /** Small uppercase heading, rendered as an <h2>. */
    title?: ReactNode;
    className?: string;
}
declare function Panel({ children, title, className }: PanelProps): react.JSX.Element;
interface NoteProps {
    children: ReactNode;
    className?: string;
}
/** A muted aside: the caveat under a control, the provenance under a figure. */
declare function Note({ children, className }: NoteProps): react.JSX.Element;
interface LiteralProps {
    children: ReactNode;
    /**
     * Announce content changes as they stream in (`aria-live="polite"`).
     * Default: `false` — a static literal should not narrate itself.
     */
    live?: boolean;
    className?: string;
}
/** Verbatim server-rendered text: a preview, a draft, a quoted source. */
declare function Literal({ children, live, className }: LiteralProps): react.JSX.Element;
interface DataTableRow {
    key: string;
    cells: ReactNode[];
}
interface DataTableProps {
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
declare function DataTable({ head, rows, rowHeader, className }: DataTableProps): react.JSX.Element | null;

declare const FI_PANEL_CLASS = "fi-panel";
declare const FI_PANEL_TITLE_CLASS = "fi-panel-title";
declare const FI_NOTE_CLASS = "fi-note";
declare const FI_LITERAL_CLASS = "fi-literal";
declare const FI_DATA_TABLE_CLASS = "fi-data-table";
/** Inject the idempotent surface stylesheet (no-op on the server / if already present). */
declare function ensureSurfaceStyle(): void;
/** Ensure the surface stylesheet is present for the lifetime of the component. */
declare function useSurfaceStyle(): void;

export { DataTable, type DataTableProps, type DataTableRow, FI_DATA_TABLE_CLASS, FI_LITERAL_CLASS, FI_NOTE_CLASS, FI_PANEL_CLASS, FI_PANEL_TITLE_CLASS, Literal, type LiteralProps, Note, type NoteProps, Panel, type PanelProps, ensureSurfaceStyle, useSurfaceStyle };
