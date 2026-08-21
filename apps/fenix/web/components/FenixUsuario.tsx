'use client';

/**
 * La píldora de usuario — con qué permisos estás trabajando y cómo cambiarlos.
 *
 * Va al pie de la barra: lo primero que se ve al abrir debe ser el trabajo, no
 * la cuenta. Pero está SIEMPRE visible, porque en el mostrador se comparte la
 * máquina y saber con qué cuenta se trabaja es lo que evita guardar una
 * cotización a nombre de quien no fue.
 *
 * Sin proveedor de identidad: el token del mostrador AUTORIZA y el correo
 * IDENTIFICA. Ver `lib/fenixSesion.ts`.
 */

import { useEffect, useRef, useState } from 'react';
import { KeyRound, LogOut, ShieldCheck, User } from 'lucide-react';
import {
  getCorreo,
  getTokenMostrador,
  getAcceso,
  setAcceso,
  setCorreo,
  setTokenMostrador,
} from '@/lib/fenixSesion';

function iniciales(texto: string): string {
  const partes = texto.trim().split(/[\s@._-]+/).filter(Boolean);
  return ((partes[0]?.[0] ?? '') + (partes[1]?.[0] ?? '')).toUpperCase() || '?';
}

export function FenixUsuario({
  admin,
  modoAbierto,
  correoConocido,
  compacto = false,
  onCambio,
}: {
  admin: boolean;
  modoAbierto: boolean;
  correoConocido: boolean;
  /** Sólo la llave, sin texto. Para el cibercafé, donde no hay barra donde
   *  anclarla y el niño no tiene por qué leer nada de cuentas. */
  compacto?: boolean;
  onCambio: () => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [correo, setCorreoLocal] = useState('');
  const [token, setTokenLocal] = useState('');
  const [acceso, setAccesoLocal] = useState('');
  // Lo que hay guardado, en estado y no leído de localStorage al pintar: el
  // servidor no tiene localStorage, así que leerlo durante el render hace que
  // pinte una píldora vacía y el cliente otra con iniciales — React tira todo
  // el árbol por esa discrepancia.
  const [guardado, setGuardado] = useState({ correo: '', token: '' });
  const caja = useRef<HTMLDivElement>(null);

  const releer = () =>
    setGuardado({ correo: getCorreo() ?? '', token: getTokenMostrador() ?? '' });

  useEffect(releer, []);

  useEffect(() => {
    setCorreoLocal(getCorreo() ?? '');
    setTokenLocal(getTokenMostrador() ?? '');
    setAccesoLocal(getAcceso() ?? '');
  }, [abierto]);

  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => {
      if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false);
    };
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && setAbierto(false);
    document.addEventListener('mousedown', fuera);
    window.addEventListener('keydown', tecla);
    return () => {
      document.removeEventListener('mousedown', fuera);
      window.removeEventListener('keydown', tecla);
    };
  }, [abierto]);

  function guardar() {
    setCorreo(correo || null);
    setTokenMostrador(token || null);
    setAcceso(acceso || null);
    releer();
    setAbierto(false);
    onCambio();
  }

  function salir() {
    setTokenMostrador(null);
    setTokenLocal('');
    releer();
    setAbierto(false);
    onCambio();
  }

  const correoGuardado = guardado.correo;
  const etiqueta = correoGuardado || (admin ? 'Mostrador' : 'Público');
  const subtitulo = modoAbierto
    ? 'sin token · acceso total'
    : admin
      ? correoConocido
        ? 'Mostrador'
        : 'Mostrador · correo no registrado'
      : 'Público · sólo chat';

  return (
    <div className="fx-user-caja" ref={caja}>
      {abierto && (
        <div className="fx-user-menu" role="dialog" aria-label="Sesión">
          {/* Primero, porque en el cibercafé es lo único que se llena: sin esto
              el asistente no contesta, y quien abre este panel ahí viene por
              esto y no por el correo. */}
          <label className="fx-user-campo">
            <span>Contraseña de la papelería</span>
            <input
              type="password"
              value={acceso}
              onChange={(e) => setAccesoLocal(e.target.value)}
              placeholder="escríbela una vez en esta PC"
            />
            <small>Deja usar el asistente de tareas. Se queda guardada en esta computadora.</small>
          </label>

          <label className="fx-user-campo">
            <span>Tu correo</span>
            <input
              value={correo}
              onChange={(e) => setCorreoLocal(e.target.value)}
              placeholder="ximena@fenix.mx"
              inputMode="email"
            />
            <small>Sólo para saber quién hizo cada cotización.</small>
          </label>

          <label className="fx-user-campo">
            <span>Token del mostrador</span>
            <input
              type="password"
              value={token}
              onChange={(e) => setTokenLocal(e.target.value)}
              placeholder="pégalo una vez en esta PC"
            />
            <small>Da acceso a los expedientes. No lo pongas en las PC del ciber.</small>
          </label>

          <div className="fx-user-acciones">
            <button type="button" className="fx-btn fx-btn-primario fi-touch-target" onClick={guardar}>
              Guardar
            </button>
            {guardado.token && (
              <button type="button" className="fx-btn fi-touch-target" onClick={salir}>
                <LogOut aria-hidden />
                Salir del mostrador
              </button>
            )}
          </div>
        </div>
      )}

      <button
        type="button"
        className={`fx-user fi-touch-target${compacto ? ' fx-user-compacto' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={abierto}
        aria-label={compacto ? 'Entrar como mostrador' : undefined}
        title={compacto ? 'Entrar como mostrador' : undefined}
        onClick={() => setAbierto((v) => !v)}
      >
        {compacto ? (
          <KeyRound aria-hidden />
        ) : (
          <>
            <span
              className={`fx-user-av${admin && !modoAbierto ? ' fx-user-av-admin' : ''}`}
              aria-hidden
            >
              {correoGuardado ? iniciales(correoGuardado) : admin ? <ShieldCheck /> : <User />}
            </span>
            <span className="fx-user-txt">
              <strong>{etiqueta}</strong>
              <span>{subtitulo}</span>
            </span>
            {/* Un correo fuera de la lista suele ser un dedazo, y deja
                cotizaciones difíciles de rastrear. Se avisa sin bloquear: no
                es una credencial. */}
            {admin && !correoConocido && (
              <span className="fx-user-alerta" aria-label="Correo no registrado" />
            )}
            {!admin && <KeyRound className="fx-user-llave" aria-hidden />}
          </>
        )}
      </button>
    </div>
  );
}
