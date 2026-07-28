'use client';

/**
 * La barra del presupuesto — el Excel donde el trabajo ocurrió.
 *
 * Cuando el modelo cierra una cotización guarda el desglose en el expediente,
 * pero para VERLO había que salir del chat, ir a Expedientes y buscar la
 * tarjeta. Eso es el laberinto que esta app vino a quitar: el entregable tiene
 * que estar donde se produjo.
 *
 * Aparece sola en cuanto la conversación abierta tiene renglones guardados, y
 * desaparece cuando no. No se pregunta ni se configura.
 */

import { Sheet } from 'lucide-react';
import type { Expediente } from '@/lib/useExpedientes';

const pesos = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 2,
});

export function FenixBarraPresupuesto({
  expediente,
  onVer,
}: {
  expediente: Expediente;
  onVer: (e: Expediente) => void;
}) {
  const renglones = (expediente.items?.length ?? 0) + (expediente.forrado?.length ?? 0);
  const incompleto = expediente.desgloseIncompleto;

  return (
    <div className={`fx-barra-pres${incompleto ? ' fx-barra-pres-alerta' : ''}`}>
      <Sheet aria-hidden />
      <div className="fx-barra-pres-txt">
        <strong>
          {incompleto ? 'Presupuesto incompleto' : 'Presupuesto listo'}
          {typeof expediente.total === 'number' && ` · ${pesos.format(expediente.total)}`}
        </strong>
        <span>
          {renglones} {renglones === 1 ? 'renglón' : 'renglones'}
          {/* El aviso va aquí y no escondido en Expedientes: si el desglose no
              llega al total que se le dio al cliente, quien está a punto de
              mandarlo tiene que enterarse ANTES, no después. */}
          {incompleto && expediente.totalDeclarado
            ? ` · la conversación decía ${pesos.format(expediente.totalDeclarado)}`
            : ''}
        </span>
      </div>
      <button
        type="button"
        className="fx-btn fx-btn-primario fi-touch-target"
        onClick={() => onVer(expediente)}
      >
        Ver presupuesto
      </button>
    </div>
  );
}
