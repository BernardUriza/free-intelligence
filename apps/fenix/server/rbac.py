"""RBAC de Fénix — dos superficies sobre la misma IA.

La papelería tiene DOS públicos en el mismo local:

- **admin** — el mostrador: cotiza, ve los expedientes de los clientes, descarga
  los Excel. Es Lidia, Ximena, Diego.
- **público** — el minicibercafé de afuera: niños haciendo tarea en PCs
  compartidas, sesiones de 10-20 minutos.

Es la MISMA IA con la misma persona; lo que cambia es qué puede tocar. Y el
riesgo concreto que esto ataca no es abstracto: sin separación, cualquiera que
abriera la app en una PC del cibercafé vería la lista completa de expedientes —
nombres de alumnos, escuelas y **WhatsApps de las mamás** de otras familias, en
una máquina donde se sienta quien sea. Son datos de menores.

POR QUÉ UNA LISTA DE CORREOS EN UNA VARIABLE Y NO UNA TABLA DE USUARIOS. Son
tres personas en un mostrador. Una tabla de usuarios exige altas, bajas, cambios
de contraseña y una pantalla para administrarlos — infraestructura para un
problema que no existe todavía. La lista se edita en el deploy, se lee al
arranque, y el día que sean quince personas se migra sin tocar a los llamadores:
la decisión vive detrás de `es_admin()`.
"""

from __future__ import annotations

import os

from fi_runner.auth import Principal


def _lista_admins() -> set[str]:
    crudo = os.getenv("FENIX_ADMIN_EMAILS", "")
    return {c.strip().lower() for c in crudo.split(",") if c.strip()}


def es_admin(principal: Principal) -> bool:
    """¿Este caller puede ver los expedientes de los clientes?

    Reglas, en orden:

    1. Sin lista configurada → **modo abierto**, para que el desarrollo local no
       exija montar Auth0. Es explícitamente inseguro y por eso el arranque lo
       grita: en un despliegue público SIN la variable, todo el mundo es admin.
    2. Con lista → sólo los correos de la lista. Cualquier otro es público,
       incluido el bearer legacy: una credencial compartida no identifica a una
       persona y no puede conceder acceso a datos de terceros.
    """
    admins = _lista_admins()
    if not admins:
        return True
    correo = (principal.email or "").strip().lower()
    return bool(correo) and correo in admins


def modo_abierto() -> bool:
    """True cuando no hay lista de admins configurada (todo el mundo es admin)."""
    return not _lista_admins()
