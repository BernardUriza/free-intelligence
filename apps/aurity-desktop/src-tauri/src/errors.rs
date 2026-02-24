// Errors — application error types for Tauri commands.

use serde::Serialize;

/// Application errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
pub enum AppError {
    #[error("{0}")]
    Io(String),
    #[error("{0}")]
    Json(String),
    #[error("{0}")]
    Config(String),
    #[error("{0}")]
    Script(String),
}

impl From<std::io::Error> for AppError {
    fn from(e: std::io::Error) -> Self {
        AppError::Io(e.to_string())
    }
}

impl From<serde_json::Error> for AppError {
    fn from(e: serde_json::Error) -> Self {
        AppError::Json(e.to_string())
    }
}
