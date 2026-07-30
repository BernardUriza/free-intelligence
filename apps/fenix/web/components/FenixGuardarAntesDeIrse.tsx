'use client';

/**
 * El único momento en que la conversación del cibercafé está a punto de
 * desaparecer: cuando alguien empieza otra.
 *
 * No hay un botón permanente de descargar porque en veinte minutos de tarea
 * nadie lo busca, y ocuparía la esquina que el chat necesita. Aparece justo
 * cuando el trabajo se va a perder, y sólo si hay trabajo que perder.
 */

import { useEffect, useRef } from 'react';
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
  const caja = useRef<HTMLDivElement>(null);

  // Escape cierra y el foco no se escapa del diálogo. Se abre con el teclado
  // (el botón de empezar otra está en el composer), así que sin esto el foco se
  // quedaba atrás en la conversación y Tab paseaba por botones tapados.
  useEffect(() => {
    const previo = document.activeElement as HTMLElement | null;
    caja.current?.querySelector<HTMLElement>('.fx-btn-primario')?.focus();

    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancelar();
        return;
      }
      if (e.key !== 'Tab' || !caja.current) return;
      const focusables = caja.current.querySelectorAll<HTMLElement>('button');
      if (!focusables.length) return;
      const primero = focusables[0];
      const ultimo = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };

    window.addEventListener('keydown', tecla);
    return () => {
      window.removeEventListener('keydown', tecla);
      previo?.focus?.();
    };
  }, [onCancelar]);

  return (
    <div className="fx-modal-fondo" role="presentation" onClick={onCancelar}>
      <div
        className="fx-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="fx-guardar-titulo"
        ref={caja}
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
