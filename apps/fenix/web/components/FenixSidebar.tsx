'use client';

/**
 * Barra lateral: la marca arriba, luego las dos vistas, luego la lista.
 *
 * Sigue siendo deliberadamente plana — sin proyectos ni carpetas. La auditoría
 * mostró que el laberinto (cuatro chats llamados casi igual, títulos con
 * `<alumno>` sin sustituir) nace de tener demasiados contenedores. Lo que se
 * agrega no es una jerarquía nueva sino una LECTURA distinta de la misma lista:
 * Cotizaciones la ordena por recencia, Expedientes por lo que le falta.
 */

import Image from 'next/image';
import { FileText, Plus, Trash2, Users } from 'lucide-react';

export type Vista = 'chats' | 'clientes';

type Conversacion = { id: string; title: string };

export function FenixSidebar({
  conversations,
  activeId,
  vista,
  disabled,
  onVista,
  onNew,
  onSwitch,
  onDelete,
}: {
  conversations: readonly Conversacion[];
  activeId: string | null;
  vista: Vista;
  disabled?: boolean;
  onVista: (v: Vista) => void;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <nav className="fx-side" aria-label="Fénix">
      <div className="fx-marca">
        <Image src="/branding/emblem.png" alt="" width={30} height={30} priority />
        <div className="fx-marca-txt">
          <strong>Fénix</strong>
          <span>Escolar AI</span>
        </div>
      </div>

      <div className="fx-tabs" role="tablist" aria-label="Vistas">
        <button
          type="button"
          role="tab"
          aria-selected={vista === 'chats'}
          className={`fx-tab fi-touch-target${vista === 'chats' ? ' fx-tab-on' : ''}`}
          onClick={() => onVista('chats')}
        >
          <FileText aria-hidden />
          Cotizaciones
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vista === 'clientes'}
          className={`fx-tab fi-touch-target${vista === 'clientes' ? ' fx-tab-on' : ''}`}
          onClick={() => onVista('clientes')}
        >
          <Users aria-hidden />
          Expedientes
        </button>
      </div>

      <button type="button" className="fx-nueva fi-touch-target" onClick={onNew} disabled={disabled}>
        <Plus aria-hidden />
        Nueva cotización
      </button>

      <ul className="fx-chats">
        {conversations.map((c) => (
          <li key={c.id} className={c.id === activeId ? 'fx-chat fx-chat-on' : 'fx-chat'}>
            <button
              type="button"
              className="fx-chat-abrir fi-touch-target"
              onClick={() => onSwitch(c.id)}
              disabled={disabled}
            >
              {c.title || 'Sin nombre'}
            </button>
            <button
              type="button"
              className="fx-chat-borrar fi-touch-target"
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
