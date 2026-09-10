'use client';

/**
 * fi-glass · un bloque que alterna VISTA y EDICIÓN.
 *
 * La máquina se queda en el consumidor a propósito: cuál campo, guardado async,
 * validación y qué cuenta como "cambió" son producto, no anatomía. Lo que sube
 * aquí es el marco que og118 escribía a mano DOS VECES en el mismo archivo — el
 * encabezado del workspace y el panel de instrucciones: un `<form>` cuando se
 * edita (para que Enter envíe), su fila de acciones, y la línea de error.
 *
 * Ningún string vive aquí. `submitSlot` y `cancelSlot` son controles del
 * consumidor; este módulo no sabe qué se está editando ni en qué idioma.
 */

import { type FormEvent, type ReactNode } from 'react';
import {
  FI_EDITABLE_ACTIONS_CLASS,
  FI_EDITABLE_CLASS,
  FI_EDITABLE_ERROR_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface EditableSectionProps {
  editing: boolean;
  /** Lo que se ve cuando NO se está editando (incluido su disparador de edición). */
  view: ReactNode;
  /** Los campos del formulario. Sólo se montan en modo edición. */
  children?: ReactNode;
  onSubmit?: (e: FormEvent<HTMLFormElement>) => void;
  /** El control primario (enviar). Del consumidor: su etiqueta y su estilo. */
  submitSlot?: ReactNode;
  /** El control secundario (cancelar). */
  cancelSlot?: ReactNode;
  /** Mensaje de error del último intento de guardado, si lo hubo. */
  error?: ReactNode;
  className?: string;
}

export function EditableSection({
  editing,
  view,
  children,
  onSubmit,
  submitSlot,
  cancelSlot,
  error,
  className,
}: EditableSectionProps) {
  useResourceStyle();
  const cls = className ? `${FI_EDITABLE_CLASS} ${className}` : FI_EDITABLE_CLASS;
  if (!editing) return <div className={cls}>{view}</div>;
  return (
    <form className={cls} onSubmit={onSubmit}>
      {children}
      {error ? <p className={FI_EDITABLE_ERROR_CLASS}>{error}</p> : null}
      {submitSlot || cancelSlot ? (
        <div className={FI_EDITABLE_ACTIONS_CLASS}>
          {submitSlot}
          {cancelSlot}
        </div>
      ) : null}
    </form>
  );
}
