'use client';

/**
 * Encabezado del chat — de quién es la cotización que tienes abierta.
 *
 * Con 33 conversaciones en la barra, entrar a una y no saber de quién es obliga
 * a leer el hilo para ubicarse. El dato ya existe en el expediente; sólo faltaba
 * mostrarlo donde se está trabajando.
 *
 * Lee el EXPEDIENTE, no el título: el título es un resumen de 60 caracteres y
 * aquí caben el alumno, su escuela con grado, el estado y el WhatsApp del tutor
 * — que es justo lo que alguien necesita a mano para llamar y cerrar la venta.
 */

import { AlertTriangle, CircleDashed, FileSpreadsheet, Loader, PackageCheck, Phone } from 'lucide-react';
import type { EstadoExpediente, Expediente } from '@/lib/useExpedientes';

const ESTADO: Record<EstadoExpediente, { etiqueta: string; icono: typeof Loader; clase: string }> = {
  nueva: { etiqueta: 'Nueva', icono: CircleDashed, clase: 'es-nueva' },
  cotizando: { etiqueta: 'Cotizando', icono: Loader, clase: 'es-cotizando' },
  bloqueada: { etiqueta: 'Falta info', icono: AlertTriangle, clase: 'es-bloqueada' },
  entregada: { etiqueta: 'Entregada', icono: FileSpreadsheet, clase: 'es-entregada' },
  cerrada: { etiqueta: 'Cerrada', icono: PackageCheck, clase: 'es-cerrada' },
};

export function FenixEncabezado({
  titulo,
  expediente,
}: {
  titulo: string | null;
  expediente: Expediente | undefined;
}) {
  if (!titulo && !expediente) return null;

  const estado = expediente ? ESTADO[expediente.estado] : null;
  const Icono = estado?.icono;
  const nombre = expediente?.alumno?.trim() || titulo || 'Cotización nueva';
  const lugar = expediente
    ? [expediente.escuela, expediente.grado].filter(Boolean).join(' · ')
    : '';

  return (
    <header className={`fx-cab ${estado?.clase ?? ''}`}>
      <div className="fx-cab-txt">
        <h2 className="fx-cab-nombre">{nombre}</h2>
        {(lugar || expediente?.folio) && (
          <p className="fx-cab-meta">
            {lugar}
            {expediente?.folio ? `${lugar ? ' · ' : ''}folio ${expediente.folio}` : ''}
          </p>
        )}
      </div>

      <div className="fx-cab-datos">
        {/* El teléfono es clicable: en el mostrador se cierra la venta llamando,
            y copiarlo a mano de un encabezado es fricción tonta. */}
        {expediente?.whatsapp && (
          <a
            className="fx-cab-tel fi-touch-target"
            href={`https://wa.me/52${expediente.whatsapp.replace(/\D/g, '')}`}
            target="_blank"
            rel="noreferrer"
          >
            <Phone aria-hidden />
            {expediente.whatsapp}
          </a>
        )}
        {estado && Icono && (
          <span className="fx-cab-estado">
            <Icono aria-hidden />
            {estado.etiqueta}
          </span>
        )}
      </div>
    </header>
  );
}
