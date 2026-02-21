// Config — first-run bootstrap, data directory, atomic file writes.

use std::fs;
use std::path::PathBuf;

use log::info;

use crate::errors::AppError;
use crate::templates;

// =============================================================================
// DATA DIRECTORY
// =============================================================================

/// Get the user data directory for Aurity (~/.aurity)
pub(crate) fn get_data_dir(_app: &tauri::AppHandle) -> Result<PathBuf, AppError> {
    // Use ~/.aurity for consistency with backend expectations
    // Note: _app parameter kept for potential future use with tauri::PathResolver
    let home =
        dirs::home_dir().ok_or(AppError::Config("Could not find home directory".into()))?;
    Ok(home.join(".aurity"))
}

// =============================================================================
// FILE UTILITIES
// =============================================================================

/// Atomically write a file: write to .tmp, then rename.
/// This prevents partial writes and is safer against TOCTOU attacks.
pub(crate) fn atomic_write(path: &PathBuf, content: &[u8]) -> Result<(), AppError> {
    let tmp_path = path.with_extension("tmp");

    // Write to temporary file
    fs::write(&tmp_path, content)
        .map_err(|e| AppError::Io(format!("Failed to write temp file {:?}: {}", tmp_path, e)))?;

    // Atomically rename to final path
    fs::rename(&tmp_path, path).map_err(|e| {
        AppError::Io(format!(
            "Failed to rename {:?} to {:?}: {}",
            tmp_path, path, e
        ))
    })?;

    Ok(())
}

/// Validate filename doesn't contain path separators (security check)
fn is_safe_filename(filename: &str) -> bool {
    !filename.contains('/') && !filename.contains('\\') && !filename.contains("..")
}

// =============================================================================
// FIRST-RUN BOOTSTRAP
// =============================================================================

/// Bootstrap configuration files on first run.
/// Extracts embedded templates to user data directory.
///
/// Security measures:
/// - Atomic writes (write to .tmp, then rename) to prevent partial state
/// - Filename validation to prevent path traversal
/// - Symlink detection to prevent symlink attacks
pub(crate) fn bootstrap_config(app: &tauri::AppHandle) -> Result<bool, AppError> {
    let data_dir = get_data_dir(app)?;
    let config_dir = data_dir.join("config");
    let personas_dir = config_dir.join("personas");
    let storage_dir = data_dir.join("storage");
    let policy_path = config_dir.join("fi.policy.yaml");

    // Check if already initialized (atomic check - file either exists or doesn't)
    if policy_path.exists() {
        // Additional safety: verify it's a regular file, not a symlink
        if policy_path.is_symlink() {
            return Err(AppError::Config(
                "Security: config file is a symlink, refusing to proceed".into(),
            ));
        }
        info!("Config already initialized at {:?}", config_dir);
        return Ok(false); // Not first run
    }

    info!(
        "First run detected - bootstrapping config to {:?}",
        data_dir
    );

    // Create directories (these are idempotent operations)
    fs::create_dir_all(&config_dir)?;
    fs::create_dir_all(&personas_dir)?;
    fs::create_dir_all(&storage_dir)?;

    // Verify directories are not symlinks (security check)
    if config_dir.is_symlink() || personas_dir.is_symlink() || storage_dir.is_symlink() {
        return Err(AppError::Config(
            "Security: one or more config directories are symlinks".into(),
        ));
    }

    // Write all persona templates first (so policy is written last as completion marker)
    for (filename, content) in templates::PERSONAS {
        // Validate filename to prevent path traversal
        if !is_safe_filename(filename) {
            return Err(AppError::Config(format!(
                "Security: invalid filename in templates: {}",
                filename
            )));
        }
        let persona_path = personas_dir.join(filename);
        atomic_write(&persona_path, content.as_bytes())?;
    }

    // Write policy template LAST (serves as "initialization complete" marker)
    atomic_write(&policy_path, templates::POLICY.as_bytes())?;

    info!("Config bootstrapped successfully!");
    info!("  - Policy: {:?}", policy_path);
    info!("  - Personas: {} files", templates::PERSONAS.len());

    Ok(true) // First run completed
}
