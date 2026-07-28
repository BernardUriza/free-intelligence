'use client';

/**
 * Lista de cotizaciones. Deliberadamente plana: sin proyectos, sin carpetas, sin
 * archivar. La auditoría mostró que el laberinto (4 chats llamados casi igual,
 * títulos con `<alumno>` sin sustituir) nace de tener demasiados contenedores.
 * Aquí sólo hay conversaciones, y el título se edita en el mismo renglón.
 */

import { Plus, Trash2 } from 'lucide-react';

type Conversacion = { id: string; title: string };

export function FenixSidebar({
  conversations,
  activeId,
  disabled,
  onNew,
  onSwitch,
  onDelete,
  onRename,
}: {
  conversations: readonly Conversacion[];
  activeId: string | null;
  disabled?: boolean;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}) {
  return (
    <nav className="fenix-sidebar" aria-label="Cotizaciones">
      <button
        type="button"
        className="fenix-new fi-touch-target"
        onClick={onNew}
        disabled={disabled}
      >
        <Plus aria-hidden />
        Nueva cotización
      </button>

      <ul className="fenix-list">
        {conversations.map((c) => (
          <li key={c.id} className={c.id === activeId ? 'fenix-item fenix-item-active' : 'fenix-item'}>
            <button
              type="button"
              className="fenix-item-open fi-touch-target"
              onClick={() => onSwitch(c.id)}
              disabled={disabled}
              onDoubleClick={() => {
                const t = window.prompt('Nombre de la cotización', c.title);
                if (t && t.trim()) onRename(c.id, t.trim());
              }}
            >
              {c.title || 'Sin nombre'}
            </button>
            <button
              type="button"
              className="fenix-item-del fi-touch-target"
              aria-label={`Borrar ${c.title || 'la cotización'}`}
              onClick={() => onDelete(c.id)}
              disabled={disabled}
            >
              <Trash2 aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
