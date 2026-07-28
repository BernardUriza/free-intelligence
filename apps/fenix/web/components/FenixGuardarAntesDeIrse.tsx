'use client';

/**
 * El único momento en que la conversación del cibercafé está a punto de
 * desaparecer: cuando alguien empieza otra.
 *
 * No hay un botón permanente de descargar porque en veinte minutos de tarea
 * nadie lo busca, y ocuparía la esquina que el chat necesita. Aparece justo
 * cuando el trabajo se va a perder, y sólo si hay trabajo que perder.
 */

import { Download, RotateCcw, X } from 'lucide-react';

export function FenixGuardarAntesDeIrse({
  turnos,
  onDescargar,
  onSeguirSinGuardar,
  onCancelar,
}: {
  turnos: number;
  onDescargar: () => void;
  onSeguirSinGuardar: () => void;
  onCancelar: () => void;
}) {
  return (
    <div className="fx-modal-fondo" role="presentation" onClick={onCancelar}>
      <div
        className="fx-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="fx-guardar-titulo"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="fx-modal-x fi-touch-target" onClick={onCancelar} aria-label="Cancelar">
          <X aria-hidden />
        </button>

        <h2 id="fx-guardar-titulo">¿Te llevas esta conversación?</h2>
        <p>
          Esta computadora no guarda nada: al empezar otra, los {turnos} mensajes de
          ésta desaparecen. Puedes descargarla como archivo y abrirla después.
        </p>

        <div className="fx-modal-acciones">
          <button type="button" className="fx-btn fx-btn-primario fi-touch-target" onClick={onDescargar}>
            <Download aria-hidden />
            Descargar y empezar otra
          </button>
          <button type="button" className="fx-btn fi-touch-target" onClick={onSeguirSinGuardar}>
            <RotateCcw aria-hidden />
            Empezar sin guardar
          </button>
        </div>
      </div>
    </div>
  );
}
