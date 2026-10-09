'use client';

/**
 * og118 start screen — the empty state of a new chat: the Og tile, what og118 is,
 * and what you can do from here. It fills the transcript region, never the viewport.
 */
export function Og118StartScreen() {
  return (
    <div className="og-start" data-ref="og118-start-screen">
      <section className="og-start-card">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className="og-start-tile"
          src="/og-tile.png"
          alt="Oganesón, elemento 118"
          width={220}
          height={220}
        />

        <h1 className="og-start-title">
          og118<span className="og-start-accent">.ai</span>
        </h1>

        <p className="og-start-element">
          Og · 118 · Oganesón: sintético, el más pesado que se conoce, el final de la tabla.
        </p>

        <p className="og-start-pitch">
          Un compañero para pensar, sobre el sustrato de Free Intelligence. Caja de cristal
          por diseño: ves el razonamiento, no sólo la respuesta.
        </p>

        <p className="og-start-hint">
          Escribe abajo, dicta con el micrófono o toca <strong>Llamar</strong> para hablar en voz.
        </p>
      </section>
    </div>
  );
}
