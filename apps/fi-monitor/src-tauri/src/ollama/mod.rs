// Ollama Integration Module
//
// Handles health checks, model management, environment variables, and
// lifecycle (start/stop) of the local Ollama instance.
//
// Module structure (SRP):
//   health.rs     — Health check and model listing helpers (reusable across modules)
//   models.rs     — Detailed model listing, pull, delete (Tauri commands)
//   env_vars.rs   — Environment variable persistence (Tauri commands)
//   lifecycle.rs  — Start/stop Ollama process (Tauri commands)

mod env_vars;
mod health;
mod lifecycle;
mod models;

// Re-export reusable helpers (used by tunnel.rs, testing.rs, main.rs)
pub(crate) use health::{check_ollama, get_ollama_models};

// Re-export Tauri commands (glob to include __cmd__ companions for generate_handler!)
pub(crate) use env_vars::*;
pub(crate) use lifecycle::*;
pub(crate) use models::*;
