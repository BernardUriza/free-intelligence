// Error classification — user-friendly messages for network, HTTP, and NSIS errors.

use super::{MonitorError, FI_MONITOR_VERSION, NSIS_EXIT_ACCESS_DENIED};
use super::paths::releases_page_url;

/// Classify a `reqwest` network-level error into a user-friendly `MonitorError`.
pub(crate) fn classify_network_error(e: &reqwest::Error) -> MonitorError {
    if e.is_timeout() {
        MonitorError::DownloadFailed(
            "La descarga tardó demasiado. Verifique su conexión a internet e intente de nuevo."
                .into(),
        )
    } else if e.is_connect() {
        MonitorError::DownloadFailed(
            "No se pudo conectar al servidor. Verifique su conexión a internet.".into(),
        )
    } else {
        MonitorError::DownloadFailed(format!(
            "Error de red al descargar FI Monitor: {}",
            e
        ))
    }
}

/// Classify an HTTP status code into a user-friendly `MonitorError`.
pub(crate) fn classify_http_status(status: reqwest::StatusCode) -> MonitorError {
    let url = releases_page_url();

    match status.as_u16() {
        404 => MonitorError::DownloadFailed(format!(
            "No se encontró la versión {} de FI Monitor. Es posible que aún no esté publicada.\n\
             Visite {} para ver las versiones disponibles.",
            FI_MONITOR_VERSION, url
        )),
        403 => MonitorError::DownloadFailed(
            "Acceso denegado al servidor de descargas. Intente de nuevo más tarde.".into(),
        ),
        _ => MonitorError::DownloadFailed(format!(
            "Error del servidor al descargar FI Monitor (HTTP {}). Intente de nuevo más tarde.",
            status.as_u16()
        )),
    }
}

/// Classify an NSIS installer failure into a user-friendly `MonitorError`.
pub(crate) fn classify_install_error(stderr: &str, exit_code: i32, installer_path: &str) -> MonitorError {
    if exit_code == NSIS_EXIT_ACCESS_DENIED {
        MonitorError::InstallFailed(format!(
            "Acceso denegado al instalar FI Monitor. \
             Ejecute Aurity como administrador e intente de nuevo.\n\
             Instalador: {}",
            installer_path
        ))
    } else if stderr.contains("Access is denied") || stderr.contains("elevation") {
        MonitorError::InstallFailed(format!(
            "Se requieren permisos de administrador para instalar FI Monitor.\n\
             Ejecute Aurity como administrador e intente de nuevo.\n\
             Instalador: {}",
            installer_path
        ))
    } else {
        MonitorError::InstallFailed(format!(
            "La instalación falló (código de salida: {}). Intente ejecutar manualmente: {}",
            exit_code, installer_path
        ))
    }
}
