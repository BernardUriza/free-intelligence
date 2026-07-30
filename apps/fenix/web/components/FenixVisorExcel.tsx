'use client';

/**
 * Visor del presupuesto — ver la hoja antes de mandarla.
 *
 * Lo que se pinta aquí es EL ARCHIVO parseado por el servidor, no una
 * re-interpretación de los datos en el cliente. Si el visor dibujara desde el
 * input, podría mostrar algo distinto a lo que se descarga; y una vista previa
 * infiel es peor que ninguna, porque se confía en ella para decidir si mandarla.
 */

import { useEffect, useState } from 'react';
import { Download, Loader2, X } from 'lucide-react';

export interface CeldaVista {
  v: string | number;
  moneda: boolean;
  negrita: boolean;
  cursiva: boolean;
  tam: number;
  fondo: string | null;
  color: string | null;
  alineado: string;
  cols: number;
  filas: number;
}

export interface HojaVista {
  nombre: string;
  filas: CeldaVista[][];
  anchos: number[];
}

const pesos = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 2,
});

export function FenixVisorExcel({
  hoja,
  cargando,
  error,
  onCerrar,
  onDescargar,
}: {
  hoja: HojaVista | null;
  cargando: boolean;
  error: string | null;
  onCerrar: () => void;
  onDescargar: () => void;
}) {
  const [descargando, setDescargando] = useState(false);

  // Escape cierra: es un panel modal y quedarse atrapado en él con el teclado
  // es la queja clásica de este patrón.
  useEffect(() => {
    const onTecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCerrar();
    };
    window.addEventListener('keydown', onTecla);
    return () => window.removeEventListener('keydown', onTecla);
  }, [onCerrar]);

  return (
    <div className="fx-visor-fondo" onClick={onCerrar} role="presentation">
      <section
        className="fx-visor"
        role="dialog"
        aria-modal="true"
        aria-label="Vista previa del presupuesto"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="fx-visor-head">
          <div className="fx-visor-titulo">
            <strong>{hoja?.nombre ?? 'Presupuesto'}</strong>
            <span>Así se ve el archivo que se manda</span>
          </div>
          <div className="fx-visor-acciones">
            <button
              type="button"
              className="fx-btn fx-btn-primario fi-touch-target"
              disabled={!hoja || descargando}
              data-estado={descargando ? 'guardando' : undefined}
              onClick={async () => {
                setDescargando(true);
                try {
                  await onDescargar();
                } finally {
                  setDescargando(false);
                }
              }}
            >
              {descargando ? <Loader2 className="fx-girando" aria-hidden /> : <Download aria-hidden />}
              {descargando ? 'Bajando…' : 'Descargar'}
            </button>
            <button
              type="button"
              className="fx-btn fi-touch-target"
              aria-label="Cerrar la vista previa"
              onClick={onCerrar}
            >
              <X aria-hidden />
            </button>
          </div>
        </header>

        <div className="fx-visor-cuerpo">
          {cargando && <p className="fx-vacio">Generando la hoja…</p>}
          {error && <p className="fx-vacio fx-error">No pude generar la vista: {error}</p>}
          {hoja && (
            <div className="fx-hoja-marco">
              <table className="fx-hoja">
                <colgroup>
                  {hoja.anchos.map((a, i) => (
                    // El ancho de columna de Excel es en caracteres; ×7.5px lo
                    // aproxima a píxeles para que la proporción se conserve.
                    <col key={i} style={{ width: `${a * 7.5}px` }} />
                  ))}
                </colgroup>
                <tbody>
                  {hoja.filas.map((fila, i) => (
                    <tr key={i}>
                      {fila.map((c, j) => (
                        <td
                          key={j}
                          colSpan={c.cols > 1 ? c.cols : undefined}
                          rowSpan={c.filas > 1 ? c.filas : undefined}
                          style={{
                            background: c.fondo ?? undefined,
                            color: c.color ?? undefined,
                            fontWeight: c.negrita ? 700 : 400,
                            fontStyle: c.cursiva ? 'italic' : undefined,
                            fontSize: `${Math.max(c.tam, 8) * 1.05}px`,
                            textAlign: c.alineado as 'left' | 'center' | 'right',
                          }}
                        >
                          {c.moneda && typeof c.v === 'number' ? pesos.format(c.v) : c.v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
