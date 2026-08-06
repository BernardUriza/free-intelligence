'use client';

/**
 * Sesión de Fénix — sin proveedor de identidad.
 *
 * Dos datos, con papeles distintos y conviene no confundirlos:
 *
 * - **token del mostrador** → AUTORIZA. Es el secreto de la papelería, se pega
 *   una vez en las PCs de adentro y vive en su localStorage. Las máquinas del
 *   cibercafé simplemente no lo tienen, que es exactamente la separación real
 *   del local: adentro vs afuera, no persona vs persona.
 * - **correo** → IDENTIFICA. Dice QUIÉN trabajó una cotización. No da acceso a
 *   nada; escribirlo mal no abre ninguna puerta, sólo hace difícil rastrear
 *   después quién la hizo.
 * - **contraseña de acceso** → DEJA ENTRAR al asistente de tareas. Separa la
 *   papelería de internet, no a una persona de otra: se teclea una vez en cada
 *   PC del cibercafé y se queda. Quien descubra la URL desde fuera no la tiene.
 *   No sustituye a la cuota de turnos: un secreto que usan varios niños termina
 *   compartido, así que el techo de gasto sigue siendo la cuota.
 */

import { authHeaders } from './fenixToken';

const LLAVE_TOKEN = 'fenix_admin_token';
const LLAVE_CORREO = 'fenix_email';
const LLAVE_ACCESO = 'fenix_acceso';

function leer(llave: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(llave);
  } catch {
    return null;
  }
}

function escribir(llave: string, valor: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (valor) window.localStorage.setItem(llave, valor.trim());
    else window.localStorage.removeItem(llave);
  } catch {
    /* modo privado */
  }
}

export const getTokenMostrador = () => leer(LLAVE_TOKEN);
export const setTokenMostrador = (v: string | null) => escribir(LLAVE_TOKEN, v);
export const getCorreo = () => leer(LLAVE_CORREO);
export const setCorreo = (v: string | null) => escribir(LLAVE_CORREO, v);
export const getAcceso = () => leer(LLAVE_ACCESO);
export const setAcceso = (v: string | null) => escribir(LLAVE_ACCESO, v);

/**
 * TODAS las cabeceras que el servidor espera: el bearer del backend más las de
 * sesión. Se leen en cada llamada para que un cambio aplique sin recargar.
 *
 * Es UNA función y no dos a propósito. Cuando eran `authHeaders()` y
 * `sesionHeaders()` por separado, olvidar la segunda no rompía nada visible —
 * el servidor simplemente atendía como público. Pasó dos veces: la librería de
 * conversaciones se ganó su propio 404, y `/chat/stream` le dio al MOSTRADOR la
 * persona del cibercafé, que contesta tareas en vez de cotizar. Ninguna de las
 * dos falló en los tests: los sitios de llamada no se testean, se olvidan.
 */
export function fenixHeaders(): Record<string, string> {
  const h: Record<string, string> = { ...authHeaders() };
  const token = getTokenMostrador();
  const correo = getCorreo();
  const acceso = getAcceso();
  if (token) h['X-Fenix-Admin'] = token;
  if (correo) h['X-Fenix-Email'] = correo;
  if (acceso) h['X-Fenix-Acceso'] = acceso;
  return h;
}
