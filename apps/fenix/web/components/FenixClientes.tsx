'use client';

/**
 * Expedientes — tarjetas, no renglones de texto.
 *
 * El expediente vivía dentro del TÍTULO del chat, y funcionó para arrancar: era
 * la convención que el equipo ya usaba a mano. Pero el título es un contenedor
 * de 60 caracteres (`TITLE_MAX` en fi-core) y para que cupiera el teléfono hubo
 * que abreviar la escuela con elipsis. Un contenedor donde un campo se mutila
 * para salvar otro no es un expediente.
 *
 * Ahora cada cliente es un objeto con campos propios y una tarjeta que se lee de
 * un vistazo: el estado manda el color, los pendientes se ven sin abrir nada, y
 * el chat de esa cotización está a un clic.
 */

import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Check,
  CircleDashed,
  FileSpreadsheet,
  Loader,
  Loader2,
  MessageSquare,
  PackageCheck,
  Phone,
  Save,
  School,
  Search,
  User,
  X,
} from 'lucide-react';
import { pendientes, type EstadoExpediente, type Expediente } from '@/lib/useExpedientes';

const ESTADO = {
  nueva: { etiqueta: 'Nueva', icono: CircleDashed, clase: 'es-nueva' },
  cotizando: { etiqueta: 'Cotizando', icono: Loader, clase: 'es-cotizando' },
  bloqueada: { etiqueta: 'Falta info', icono: AlertTriangle, clase: 'es-bloqueada' },
  entregada: { etiqueta: 'Entregada', icono: FileSpreadsheet, clase: 'es-entregada' },
  cerrada: { etiqueta: 'Cerrada', icono: PackageCheck, clase: 'es-cerrada' },
} as const satisfies Record<EstadoExpediente, { etiqueta: string; icono: unknown; clase: string }>;

const ORDEN: EstadoExpediente[] = ['bloqueada', 'cotizando', 'nueva', 'entregada', 'cerrada'];

export function FenixClientes({
  expedientes,
  cargando,
  error,
  onGuardar,
  onAbrirChat,
}: {
  expedientes: Expediente[];
  cargando: boolean;
  error: string | null;
  onGuardar: (datos: Partial<Expediente>) => Promise<unknown>;
  onAbrirChat: (conversacionId: string) => void;
}) {
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<EstadoExpediente | 'todos'>('todos');
  const [editando, setEditando] = useState<string | null>(null);
  const [borrador, setBorrador] = useState<Partial<Expediente> | null>(null);
  // El guardado viaja por la red: sin un estado explícito el botón se queda
  // mudo y el usuario vuelve a picarle creyendo que no registró.
  const [guardando, setGuardando] = useState(false);
  const [recienGuardado, setRecienGuardado] = useState<string | null>(null);

  const conteo = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of expedientes) c[e.estado] = (c[e.estado] ?? 0) + 1;
    return c;
  }, [expedientes]);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return expedientes
      .filter((e) => (filtro === 'todos' ? true : e.estado === filtro))
      .filter((e) =>
        q ? `${e.alumno} ${e.escuela} ${e.grado} ${e.whatsapp} ${e.tutor} ${e.folio}`.toLowerCase().includes(q) : true,
      )
      // Lo que estorba primero: una cotización bloqueada es dinero detenido.
      .sort((a, b) => ORDEN.indexOf(a.estado) - ORDEN.indexOf(b.estado));
  }, [expedientes, busqueda, filtro]);

  async function guardar() {
    if (!borrador || guardando) return;
    setGuardando(true);
    try {
      await onGuardar(borrador);
      // La lista se reordena sola al cambiar el estado, así que la tarjeta
      // destella una vez para decir CUÁL se movió.
      setRecienGuardado(borrador.id ?? null);
      setTimeout(() => setRecienGuardado(null), 1200);
      setEditando(null);
      setBorrador(null);
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) return <p className="fx-vacio">Cargando expedientes…</p>;
  if (error) return <p className="fx-vacio fx-error">No pude leer los expedientes: {error}</p>;

  return (
    <section className="fx-clientes">
      <header className="fx-clientes-head">
        <div>
          <h2 className="fx-clientes-title">Expedientes</h2>
          <p className="fx-clientes-sub">
            {conteo.bloqueada ? `${conteo.bloqueada} esperando datos · ` : ''}
            {expedientes.length} clientes
          </p>
        </div>
        <label className="fx-buscar">
          <Search aria-hidden />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar alumno, escuela, teléfono o folio"
            aria-label="Buscar expediente"
          />
        </label>
      </header>

      <div className="fx-filtros" role="tablist" aria-label="Filtrar por estado">
        <button
          type="button"
          role="tab"
          aria-selected={filtro === 'todos'}
          className={`fx-chip${filtro === 'todos' ? ' fx-chip-on' : ''}`}
          onClick={() => setFiltro('todos')}
        >
          Todos <span>{expedientes.length}</span>
        </button>
        {ORDEN.filter((e) => conteo[e]).map((e) => (
          <button
            key={e}
            type="button"
            role="tab"
            aria-selected={filtro === e}
            className={`fx-chip ${ESTADO[e].clase}${filtro === e ? ' fx-chip-on' : ''}`}
            onClick={() => setFiltro(e)}
          >
            {ESTADO[e].etiqueta} <span>{conteo[e]}</span>
          </button>
        ))}
      </div>

      <div className="fx-tarjetas">
        {visibles.map((e) => {
          const falta = pendientes(e);
          const Icono = ESTADO[e.estado].icono as React.ComponentType<{ 'aria-hidden'?: boolean }>;
          const enEdicion = editando === e.id;

          if (enEdicion && borrador) {
            return (
              <article key={e.id} className={`fx-tarjeta ${ESTADO[e.estado].clase} fx-tarjeta-edit`}>
                <form
                  className="fx-form"
                  onSubmit={(ev) => {
                    ev.preventDefault();
                    void guardar();
                  }}
                >
                  <div className="fx-campos">
                    <label>
                      <span>Alumno</span>
                      <input
                        autoFocus
                        value={borrador.alumno ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, alumno: ev.target.value })}
                        placeholder="Nombre y apellido"
                      />
                    </label>
                    <label>
                      <span>Escuela</span>
                      <input
                        value={borrador.escuela ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, escuela: ev.target.value })}
                        placeholder="Urbana 100"
                      />
                    </label>
                    <label>
                      <span>Grado</span>
                      <input
                        value={borrador.grado ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, grado: ev.target.value })}
                        placeholder="4°A"
                      />
                    </label>
                    <label>
                      <span>Mamá o tutor</span>
                      <input
                        value={borrador.tutor ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, tutor: ev.target.value })}
                        placeholder="Jessica Rubí"
                      />
                    </label>
                    <label>
                      <span>WhatsApp</span>
                      <input
                        inputMode="tel"
                        value={borrador.whatsapp ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, whatsapp: ev.target.value })}
                        placeholder="33 1234 5678"
                      />
                    </label>
                    <label>
                      <span>Folio</span>
                      <input
                        value={borrador.folio ?? ''}
                        onChange={(ev) => setBorrador({ ...borrador, folio: ev.target.value })}
                        placeholder="1145"
                      />
                    </label>
                    <label>
                      <span>Estado</span>
                      <select
                        value={borrador.estado ?? 'nueva'}
                        onChange={(ev) =>
                          setBorrador({ ...borrador, estado: ev.target.value as EstadoExpediente })
                        }
                      >
                        {ORDEN.map((k) => (
                          <option key={k} value={k}>
                            {ESTADO[k].etiqueta}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Total</span>
                      <input
                        inputMode="decimal"
                        value={borrador.total ?? ''}
                        onChange={(ev) =>
                          setBorrador({
                            ...borrador,
                            total: ev.target.value ? Number(ev.target.value) : null,
                          })
                        }
                        placeholder="1407.15"
                      />
                    </label>
                  </div>
                  <div className="fx-acciones">
                    <button
                      type="submit"
                      className="fx-btn fx-btn-primario fi-touch-target"
                      data-estado={guardando ? 'guardando' : undefined}
                      disabled={guardando}
                    >
                      {guardando ? <Loader2 className="fx-girando" aria-hidden /> : <Save aria-hidden />}
                      {guardando ? 'Guardando…' : 'Guardar'}
                    </button>
                    <button
                      type="button"
                      className="fx-btn fi-touch-target"
                      disabled={guardando}
                      onClick={() => {
                        setEditando(null);
                        setBorrador(null);
                      }}
                    >
                      <X aria-hidden />
                      Cancelar
                    </button>
                  </div>
                </form>
              </article>
            );
          }

          return (
            <article
              key={e.id}
              className={`fx-tarjeta ${ESTADO[e.estado].clase}`}
              {...(recienGuardado === e.id ? { 'data-recien': '' } : {})}
            >
              <header className="fx-t-head">
                <span className="fx-t-estado">
                  <Icono aria-hidden />
                  {ESTADO[e.estado].etiqueta}
                </span>
                {e.folio && <span className="fx-t-folio">#{e.folio}</span>}
              </header>

              <h3 className="fx-t-nombre">
                <User aria-hidden />
                {e.alumno || 'Sin nombre'}
              </h3>

              <dl className="fx-t-datos">
                {(e.escuela || e.grado) && (
                  <div>
                    <dt>
                      <School aria-hidden />
                    </dt>
                    <dd>
                      {e.escuela || 'Escuela por definir'}
                      {e.grado && ` · ${e.grado}`}
                    </dd>
                  </div>
                )}
                {e.whatsapp && (
                  <div>
                    <dt>
                      <Phone aria-hidden />
                    </dt>
                    <dd>
                      {e.whatsapp}
                      {e.tutor && ` · ${e.tutor}`}
                    </dd>
                  </div>
                )}
              </dl>

              {typeof e.total === 'number' && (
                <p className="fx-t-total">
                  ${e.total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </p>
              )}

              {falta.length > 0 && (
                <p className="fx-t-falta">
                  <AlertTriangle aria-hidden />
                  Falta {falta.join(', ')}
                </p>
              )}

              <footer className="fx-t-pie">
                <button
                  type="button"
                  className="fx-btn fi-touch-target"
                  onClick={() => {
                    setEditando(e.id);
                    setBorrador({ ...e });
                  }}
                >
                  {falta.length ? <AlertTriangle aria-hidden /> : <Check aria-hidden />}
                  {falta.length ? 'Completar' : 'Editar'}
                </button>
                {e.conversacionId && (
                  <button
                    type="button"
                    className="fx-btn fx-btn-fantasma fi-touch-target"
                    onClick={() => onAbrirChat(e.conversacionId as string)}
                  >
                    <MessageSquare aria-hidden />
                    Cotización
                  </button>
                )}
              </footer>
            </article>
          );
        })}
      </div>

      {visibles.length === 0 && <p className="fx-vacio">Nada con ese filtro.</p>}
    </section>
  );
}
