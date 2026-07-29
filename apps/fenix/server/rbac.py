"""RBAC de Fénix — dos superficies sobre la misma IA, sin proveedor de identidad.

La papelería tiene DOS públicos en el mismo local:

- **mostrador (admin)** — cotiza, ve los expedientes de los clientes, descarga
  los Excel. Son Lidia, Ximena, Diego.
- **cibercafé (público)** — niños haciendo tarea en PCs compartidas, sesiones
  de 10-20 minutos.

Misma IA, misma persona; cambia lo que puede tocar. Sin separación, cualquiera
en el cibercafé vería la lista completa de expedientes: nombres de alumnos,
escuelas y WhatsApps de las mamás de otras familias. Datos de menores en una
máquina pública.

## Por qué un token de mostrador y no un proveedor de identidad

Auth0 —o cualquier IdP— exige tenant, callbacks por entorno, refresh tokens y
consentimiento, para distinguir a tres personas que trabajan detrás del mismo
mostrador. La separación real aquí no es entre personas: es entre **las PCs de
adentro y las de afuera**. Un secreto que vive en las máquinas del mostrador
modela exactamente eso, y se revoca cambiando una variable de entorno.

El correo (`X-Fenix-Email`) sirve para saber QUIÉN trabajó una cotización, no
para autorizar: es identificación, no credencial. Autoriza el token.
"""

from __future__ import annotations

import hmac
import os


def _token_mostrador() -> str:
    return (os.getenv("FENIX_ADMIN_TOKEN") or "").strip()


def _correos_conocidos() -> set[str]:
    crudo = os.getenv("FENIX_ADMIN_EMAILS", "")
    return {c.strip().lower() for c in crudo.split(",") if c.strip()}


def modo_abierto() -> bool:
    """Todo el mundo es mostrador. Requiere pedirlo a propósito — ver `exigir_config`."""
    return not _token_mostrador()


class ConfiguracionInsegura(RuntimeError):
    """El servidor arrancaría con los expedientes abiertos y nadie lo pidió."""


def exigir_config() -> None:
    """Falla el arranque si la configuración deja el negocio abierto sin querer.

    Antes esto era un warning al arrancar. Un warning en un log no es un
    guardia: nadie lee la salida de un contenedor que arrancó bien, así que un
    deploy que olvidara `FENIX_ADMIN_TOKEN` servía la lista completa de
    expedientes —nombres de alumnos, escuelas, WhatsApps de las mamás— y se veía
    exactamente igual que uno correcto.

    El modo abierto sigue existiendo porque en local es cómodo, pero ahora hay
    que TECLEARLO: `FENIX_MODO_ABIERTO=1`. Un estado inseguro que se alcanza por
    omisión es un accidente esperando; uno que exige una variable explícita es
    una decisión.
    """
    if _token_mostrador():
        return
    if (os.getenv("FENIX_MODO_ABIERTO") or "").strip() in ("1", "true", "yes"):
        return
    raise ConfiguracionInsegura(
        "sin FENIX_ADMIN_TOKEN los expedientes quedan abiertos a cualquiera que "
        "alcance el servidor. Pon el token, o declara el modo abierto a "
        "propósito con FENIX_MODO_ABIERTO=1 (sólo para local)."
    )


def es_admin(token_recibido: str | None) -> bool:
    esperado = _token_mostrador()
    if not esperado:
        return True
    # Comparación en tiempo constante: un `==` filtra el token carácter a
    # carácter ante quien pueda medir la respuesta.
    return bool(token_recibido) and hmac.compare_digest(token_recibido.strip(), esperado)


def correo_conocido(correo: str | None) -> bool:
    """¿Este correo está en la lista de la papelería?

    NO autoriza — el token ya lo hizo. Sirve para marcar en la interfaz cuando
    alguien trabaja con un correo que nadie registró, que suele significar un
    dedazo al escribirlo y una cotización difícil de rastrear después.
    """
    conocidos = _correos_conocidos()
    if not conocidos:
        return True
    return bool(correo) and correo.strip().lower() in conocidos
