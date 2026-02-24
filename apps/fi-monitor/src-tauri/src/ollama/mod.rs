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

// Re-export Tauri commands
pub(crate) use env_vars::{get_env_vars, set_env_vars};
pub(crate) use lifecycle::{start_ollama, stop_ollama};
pub(crate) use models::{delete_ollama_model, list_ollama_models_detailed, pull_ollama_model};
