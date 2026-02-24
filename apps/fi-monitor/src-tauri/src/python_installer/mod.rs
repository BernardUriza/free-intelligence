// Python 3.14 installation — detection and install commands.

mod detection;
mod install;

pub(crate) use detection::*;
pub(crate) use install::*;

use serde::Serialize;

/// Status of a Python installation check.
#[derive(Serialize)]
pub struct PythonInstallStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub install_path: Option<String>,
}
