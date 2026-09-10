'use client';

/**
 * fi-glass · una sección de lista dentro de un workspace.
 *
 * Cabecera (título + una acción) sobre filas de (título, meta). No sabe qué se
 * lista: og118 pone ahí las conversaciones de un proyecto, y el módulo no
 * aprende esa palabra. El estado vacío y el de carga son `children` del
 * consumidor — un componente que trae su propio "no hay nada todavía" ya
 * aprendió un idioma.
 */

import { type ReactNode } from 'react';
import {
  FI_LIST_CLASS,
  FI_LIST_HEAD_CLASS,
  FI_LIST_ITEMS_CLASS,
  FI_LIST_ROW_CLASS,
  FI_LIST_ROW_META_CLASS,
  FI_LIST_ROW_TITLE_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface ResourceListSectionProps {
  /** Un string se envuelve en `<h2>`; un nodo se usa tal cual. */
  title: ReactNode;
  /** Control al final de la fila de cabecera (p. ej. "nuevo"). */
  actionSlot?: ReactNode;
  children: ReactNode;
  /** Etiqueta accesible de la sección. */
  ariaLabel?: string;
  className?: string;
}

export function ResourceListSection({
  title,
  actionSlot,
  children,
  ariaLabel,
  className,
}: ResourceListSectionProps) {
  useResourceStyle();
  return (
    <section
      className={className ? `${FI_LIST_CLASS} ${className}` : FI_LIST_CLASS}
      aria-label={ariaLabel}
    >
      <div className={FI_LIST_HEAD_CLASS}>
        {typeof title === 'string' ? <h2>{title}</h2> : title}
        {actionSlot}
      </div>
      {children}
    </section>
  );
}

export interface ResourceListItemsProps {
  children: ReactNode;
  className?: string;
}

export function ResourceListItems({ children, className }: ResourceListItemsProps) {
  useResourceStyle();
  return (
    <ul className={className ? `${FI_LIST_ITEMS_CLASS} ${className}` : FI_LIST_ITEMS_CLASS}>
      {children}
    </ul>
  );
}

export interface ResourceListRowProps {
  title: ReactNode;
  /** Columna derecha: fecha relativa, conteo, estado. Ya formateada por el consumidor. */
  meta?: ReactNode;
  onSelect?: () => void;
  className?: string;
}

export function ResourceListRow({ title, meta, onSelect, className }: ResourceListRowProps) {
  useResourceStyle();
  return (
    <li>
      <button
        type="button"
        className={className ? `${FI_LIST_ROW_CLASS} ${className}` : FI_LIST_ROW_CLASS}
        onClick={onSelect}
      >
        <span className={FI_LIST_ROW_TITLE_CLASS}>{title}</span>
        {meta ? <span className={FI_LIST_ROW_META_CLASS}>{meta}</span> : null}
      </button>
    </li>
  );
}
