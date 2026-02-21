// Ollama Installer Module
//
// Handles detection and automatic installation of Ollama.
// On Windows, OllamaSetup.exe is bundled in src-tauri/binaries/ and installed
// silently when FI Monitor detects Ollama is not available.
//
// Module structure (SRP):
//   detection.rs — Check if Ollama is installed, find executable path
//   install.rs   — Silent install from bundle or download from ollama.com

mod detection;
mod install;

use serde::Serialize;

// Re-export types
#[derive(Serialize)]
pub struct OllamaInstallStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub install_path: Option<String>,
}

// Re-export Tauri commands
pub use detection::check_ollama_installed;
pub use install::{download_and_install_ollama, install_ollama_silent};
