'use client';

/**
 * Barra lateral: la marca arriba, las dos vistas, y las cotizaciones como
 * MINI-TARJETAS.
 *
 * Antes era una lista de títulos truncados (`28 jul — Sofía Ramírez (Sec.
 * Gó…`), y el corte caía justo encima del dato: en 290px de ancho, un renglón
 * de texto plano gasta la mitad en la fecha y la otra mitad la pierde en la
 * elipsis. La tarjeta usa dos líneas y una franja de color, así que en el mismo
 * espacio caben el alumno, la escuela y el estado — legibles.
 *
 * Los datos NO se parsean del título: se leen del expediente, cruzado por
 * `conversacionId`. El título es un resumen; el expediente es la verdad.
 */

import Image from 'next/image';
import { FileText, Plus, Trash2, Users } from 'lucide-react';
import type { EstadoExpediente, Expediente } from '@/lib/useExpedientes';

export type Vista = 'chats' | 'clientes';

type Conversacion = { id: string; title: string };

const CLASE_ESTADO: Record<EstadoExpediente, string> = {
  nueva: 'es-nueva',
  cotizando: 'es-cotizando',
  bloqueada: 'es-bloqueada',
  entregada: 'es-entregada',
  cerrada: 'es-cerrada',
};

/** Fecha corta desde el título (`28 jul 1pm — …`), que es donde el equipo la puso. */
function fechaDe(titulo: string): string {
  const m = titulo.match(/^(\d{1,2}\s+\w{3,})/);
  return m ? m[1] : '';
}

export function FenixSidebar({
  conversations,
  expedientes,
  activeId,
  vista,
  disabled,
  onVista,
  onNew,
  onSwitch,
  onDelete,
}: {
  conversations: readonly Conversacion[];
  expedientes: Expediente[];
  activeId: string | null;
  vista: Vista;
  disabled?: boolean;
  onVista: (v: Vista) => void;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const porConversacion = new Map(
    expedientes.filter((e) => e.conversacionId).map((e) => [e.conversacionId as string, e]),
  );

  return (
    <nav className="fx-side" aria-label="Fénix">
      <div className="fx-marca">
        {/* emblem-64 y no emblem.png: el master pesa 234 KB para pintar 30
            píxeles. A 64px (2x para retina) son 3.6 KB. */}
        <Image src="/branding/emblem-64.png" alt="" width={32} height={32} priority />
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
        {conversations.map((c) => {
          const e = porConversacion.get(c.id);
          const clase = e ? CLASE_ESTADO[e.estado] : '';
          const alumno = e?.alumno?.trim() || 'Sin nombre';
          const lugar = e ? [e.escuela, e.grado].filter(Boolean).join(' · ') : '';
          const fecha = fechaDe(c.title);

          return (
            <li
              key={c.id}
              className={`fx-mini ${clase}${c.id === activeId ? ' fx-mini-on' : ''}`}
            >
              <button
                type="button"
                className="fx-mini-abrir fi-touch-target"
                onClick={() => onSwitch(c.id)}
                disabled={disabled}
                title={c.title}
              >
                <span className="fx-mini-l1">
                  <span className="fx-mini-nombre">{alumno}</span>
                  {fecha && <span className="fx-mini-fecha">{fecha}</span>}
                </span>
                <span className="fx-mini-l2">{lugar || c.title}</span>
              </button>
              <button
                type="button"
                className="fx-mini-borrar fi-touch-target"
                aria-label={`Borrar la cotización de ${alumno}`}
                onClick={() => onDelete(c.id)}
                disabled={disabled}
              >
                <Trash2 aria-hidden />
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
