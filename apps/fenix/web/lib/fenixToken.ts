'use client';

/**
 * Token de acceso de fenix — se lee en RUNTIME de localStorage, nunca se hornea
 * en el bundle estático.
 *
 * ALCANCE (ToS): fenix corre contra el mismo backend que og118, que autentica el
 * modelo con el CLAUDE_CODE_OAUTH_TOKEN personal de Bernard (suscripción Max).
 * Servir a terceros con esa credencial rompe el ToS de Anthropic — por eso esta
 * app es de uso PERSONAL (Bernard + Claude, fase de dogfood). El día que el
 * equipo de la papelería la use, necesita su propia cuenta o una API key del
 * negocio. Ver memoria [[og118-oauth-personal-use]].
 *
 * HALLAZGO-3: este módulo es idéntico al og118Token salvo el nombre de la llave.
 * Otro candidato a subir al framework.
 */

const KEY = 'fenix_access_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(KEY, token.trim());
  } catch {
    /* modo privado — el token no persiste */
  }
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/**
 * INTERNA — sólo la usa `fenixHeaders()` en `fenixSesion.ts`.
 *
 * Una llamada al servidor con esto y nada más viaja SIN el token del mostrador,
 * así que el servidor la atiende como público: la lista de conversaciones
 * responde 404 y `/chat/stream` contesta con la persona del cibercafé. No falla
 * ruidosamente — hace algo distinto de lo que quien escribió la llamada creía.
 * Usa `fenixHeaders()`.
 */
export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export const AUTH401 = 'AUTH401';
