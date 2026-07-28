'use client';

/**
 * Expedientes — la respuesta al hallazgo más caro de la auditoría.
 *
 * 43 de los 79 turnos bloqueados (54%) lo estaban por "falta nombre / WhatsApp".
 * Una sesión pidió el mismo dato SEIS veces, y cada repetición es un turno
 * completo del modelo releyendo la conversación entera. Pedirlo por chat es la
 * forma más cara posible de capturar dos campos de texto.
 *
 * Aquí se capturan en un formulario y se escriben en el título de la
 * conversación, que es donde el equipo ya los guardaba y donde el asistente los
 * lee. Cero backend nuevo, cero segunda verdad.
 */

import { useMemo, useState } from 'react';
import { Check, Search, UserRound } from 'lucide-react';
import { faltantes, parseCliente, tieneNombre, tituloDeCliente, type Cliente } from '@/lib/cliente';

interface Conversacion {
  id: string;
  title: string;
}

export function FenixClientes({
  conversations,
  onSave,
  onOpen,
}: {
  conversations: readonly Conversacion[];
  onSave: (id: string, titulo: string) => void;
  onOpen: (id: string) => void;
}) {
  const [busqueda, setBusqueda] = useState('');
  const [editando, setEditando] = useState<string | null>(null);
  const [borrador, setBorrador] = useState<Cliente | null>(null);

  const expedientes = useMemo(() => {
    const todos = conversations.map((c) => ({ ...c, cliente: parseCliente(c.title) }));
    const q = busqueda.trim().toLowerCase();
    const filtrados = q
      ? todos.filter((e) => `${e.cliente.alumno} ${e.cliente.escuela} ${e.cliente.whatsapp}`.toLowerCase().includes(q))
      : todos;
    // Los incompletos primero: son los que cuestan dinero cada vez que alguien
    // abre esa cotización y el asistente se traba pidiendo el dato.
    return filtrados.sort((a, b) => Number(a.cliente.completo) - Number(b.cliente.completo));
  }, [conversations, busqueda]);

  const incompletos = expedientes.filter((e) => !e.cliente.completo).length;

  function abrirEdicion(id: string, cliente: Cliente) {
    setEditando(id);
    setBorrador({ ...cliente, alumno: tieneNombre(cliente) ? cliente.alumno : '', whatsapp: cliente.whatsapp });
  }

  function guardar(id: string) {
    if (!borrador) return;
    onSave(id, tituloDeCliente(borrador));
    setEditando(null);
    setBorrador(null);
  }

  return (
    <section className="fx-clientes">
      <header className="fx-clientes-head">
        <div>
          <h2 className="fx-clientes-title">Expedientes</h2>
          <p className="fx-clientes-sub">
            {incompletos > 0
              ? `${incompletos} de ${expedientes.length} sin completar`
              : `${expedientes.length} expedientes completos`}
          </p>
        </div>
        <label className="fx-buscar">
          <Search aria-hidden />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar alumno, escuela o teléfono"
            aria-label="Buscar expediente"
          />
        </label>
      </header>

      <ul className="fx-lista">
        {expedientes.map(({ id, cliente }) => {
          const falta = faltantes(cliente);
          const enEdicion = editando === id;
          return (
            <li key={id} className={`fx-card${cliente.completo ? ' fx-card-ok' : ''}`}>
              {enEdicion && borrador ? (
                <form
                  className="fx-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    guardar(id);
                  }}
                >
                  <div className="fx-campos">
                    <label>
                      <span>Alumno</span>
                      <input
                        autoFocus
                        value={borrador.alumno}
                        onChange={(e) => setBorrador({ ...borrador, alumno: e.target.value })}
                        placeholder="Nombre y apellido"
                      />
                    </label>
                    <label>
                      <span>Escuela y grado</span>
                      <input
                        value={borrador.escuela}
                        onChange={(e) => setBorrador({ ...borrador, escuela: e.target.value })}
                        placeholder="Urbana 100, 4°A"
                      />
                    </label>
                    <label>
                      <span>WhatsApp</span>
                      <input
                        inputMode="tel"
                        value={borrador.whatsapp}
                        onChange={(e) => setBorrador({ ...borrador, whatsapp: e.target.value })}
                        placeholder="33 1234 5678"
                      />
                    </label>
                  </div>
                  <div className="fx-acciones">
                    <button type="submit" className="fx-btn fx-btn-primario fi-touch-target">
                      Guardar
                    </button>
                    <button
                      type="button"
                      className="fx-btn fi-touch-target"
                      onClick={() => {
                        setEditando(null);
                        setBorrador(null);
                      }}
                    >
                      Cancelar
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="fx-avatar" aria-hidden>
                    {cliente.completo ? <Check /> : <UserRound />}
                  </div>
                  <div className="fx-datos">
                    <button type="button" className="fx-nombre" onClick={() => onOpen(id)}>
                      {tieneNombre(cliente) ? cliente.alumno : 'Sin nombre'}
                    </button>
                    <p className="fx-meta">
                      {cliente.escuela || 'Escuela por definir'}
                      {cliente.whatsapp && ` · ${cliente.whatsapp}`}
                      {cliente.fecha && ` · ${cliente.fecha}`}
                    </p>
                    {falta.length > 0 && <p className="fx-falta">Falta {falta.join(' y ')}</p>}
                  </div>
                  <button
                    type="button"
                    className="fx-btn fi-touch-target"
                    onClick={() => abrirEdicion(id, cliente)}
                  >
                    {cliente.completo ? 'Editar' : 'Completar'}
                  </button>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
