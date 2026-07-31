import Image from 'next/image';
import Link from 'next/link';
import './landing.css';

const WHATSAPP = '5213338582967';

export default function Landing() {
  return (
    <div className="lp">
      <header className="lp-hero lp-ancho">
        {/* El emblema recortado + el nombre como TEXTO. El logo-full.png trae
            su fondo oscuro horneado (se diseñó para la app) y sobre papel se ve
            como calcomanía pegada. Además, así el nombre escala nítido y
            responde al tipo del sistema en vez de ser píxeles. */}
        <div className="lp-marca">
          <Image
            className="lp-ave"
            src="/branding/emblem-transparente.png"
            alt=""
            width={512}
            height={512}
            priority
          />
          <p className="lp-nombre">
            Fénix
            <span>Servicios Papeleros</span>
          </p>
        </div>
        <h1>
          La lista de tu hijo, <em>cotizada el mismo día</em>
        </h1>
        <p>
          Mándanos la foto de la lista escolar por WhatsApp. Te regresamos el presupuesto
          completo con el descuento de temporada, listo para que decidas — sin ir a
          preguntar precio por precio.
        </p>
        <div className="lp-acciones">
          <a
            className="lp-btn lp-btn-fuego"
            href={`https://wa.me/${WHATSAPP}?text=${encodeURIComponent('Hola, quiero cotizar una lista escolar')}`}
          >
            Mandar mi lista por WhatsApp
          </a>
          <a className="lp-btn lp-btn-linea" href="#visitar">
            Cómo llegar
          </a>
        </div>
      </header>

      <section className="lp-seccion lp-ancho">
        <h2>Cómo funciona</h2>
        <p className="lp-bajada">
          Tres pasos. El más lento es el que haces tú.
        </p>
        <div className="lp-tarjetas">
          <article className="lp-tarjeta">
            <div className="lp-num">1</div>
            <h3>Nos mandas la foto</h3>
            <p>
              La lista tal como te la dieron en la escuela. Si tachaste lo que ya tienes,
              respetamos los tachones.
            </p>
          </article>
          <article className="lp-tarjeta">
            <div className="lp-num">2</div>
            <h3>Te llega el presupuesto</h3>
            <p>
              Artículo por artículo, con el precio de lista y el descuento aplicado, en un
              archivo que puedes guardar o enseñar en casa.
            </p>
          </article>
          <article className="lp-tarjeta">
            <div className="lp-num">3</div>
            <h3>Pasas por todo junto</h3>
            <p>
              Lo dejamos armado. Si quieres, también forrado y rotulado con el nombre de tu
              hijo, listo para el primer día.
            </p>
          </article>
        </div>
      </section>

      <section className="lp-seccion lp-ancho">
        <h2>Además hacemos</h2>
        <div className="lp-tarjetas">
          <article className="lp-tarjeta">
            <h3>Forrado y rotulado</h3>
            <p>Cuadernos y carpetas forrados con lustre y plástico, rotulados por materia.</p>
          </article>
          <article className="lp-tarjeta">
            <h3>Documentos e impresión</h3>
            <p>Contratos, escritos, formatos y etiquetas. Copias, engargolados y micas.</p>
          </article>
          <article className="lp-tarjeta">
            <h3>Papelería del día a día</h3>
            <p>Lo que se acaba a media semana y no da tiempo de ir más lejos a buscarlo.</p>
          </article>
        </div>
      </section>

      <div className="lp-franja">
        <section className="lp-seccion lp-ancho">
          <div>
            <h2>
              Una investigación o un reporte, <em>en minutos</em>
            </h2>
            <p className="lp-bajada">
              Afuera tenemos dos computadoras con internet. Traen un asistente que ayuda a
              sacar el trabajo escolar rápido — <strong>sin hacer trampa</strong>. Arma el
              índice con el niño, busca los datos y dice de dónde salieron; el niño escribe
              y el asistente le revisa.
            </p>
          </div>
          <ul className="lp-lista">
            <li>Busca los datos y dice de qué página salieron: un reporte con fuentes vale más que uno bonito.</li>
            <li>Explica matemáticas paso a paso, no sólo el resultado.</li>
            <li>Revisa lo que el niño escribió — no lo escribe por él.</li>
            <li>No guarda la conversación: al terminar, se borra.</li>
          </ul>
        </section>
      </div>

      <section className="lp-seccion lp-ancho" id="visitar">
        <h2>Visítanos</h2>
        <p className="lp-bajada">
          Estamos en San Juan Bosco. Si vienes con la lista en la mano, también te la
          cotizamos ahí mismo.
        </p>
        <div className="lp-datos">
          <div className="lp-dato">
            <span>Dirección</span>
            <strong>C. José María Gómez 476, San Juan Bosco, Guadalajara</strong>
          </div>
          <div className="lp-dato">
            <span>WhatsApp</span>
            <a href={`https://wa.me/${WHATSAPP}`}>33 3858 2967</a>
          </div>
          <div className="lp-dato">
            <span>Teléfono</span>
            <a href="tel:+523333458226">33 3345 8226</a>
          </div>
        </div>
      </section>

      <footer className="lp-pie lp-ancho">
        <p>
          Servicios Papeleros Fénix · Guadalajara, Jalisco ·{' '}
          <Link href="/app/">Entrar al mostrador</Link>
        </p>
      </footer>
    </div>
  );
}
