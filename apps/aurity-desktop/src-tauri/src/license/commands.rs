use std::fs;

use super::renewal::{check_renewal_status, register_for_renewal, request_renewal};
use super::storage::{activate_license, clear_license, get_auth0_config, get_license_status};
use super::types::{
    Auth0Config, LicenseError, LicensePayload, LicenseValidationResult, RenewalResponse,
    RenewalStatus,
};
use super::crypto::validate_license;

/// Validate a license key (Tauri command)
#[tauri::command]
pub fn validate_license_key(key: String) -> LicenseValidationResult {
    validate_license(&key)
}

/// Activate a license key (Tauri command)
#[tauri::command]
pub fn activate_license_key(key: String) -> Result<LicensePayload, LicenseError> {
    activate_license(&key)
}

/// Get current license status (Tauri command)
#[tauri::command]
pub fn get_current_license_status() -> LicenseValidationResult {
    get_license_status()
}

/// Get Auth0 config from license (Tauri command)
#[tauri::command]
pub fn get_license_auth0_config() -> Result<Auth0Config, LicenseError> {
    get_auth0_config()
}

/// Check if a feature is enabled (Tauri command)
#[tauri::command]
pub fn check_feature_enabled(feature: String) -> bool {
    let status = get_license_status();
    status
        .payload
        .map(|p| p.has_feature(&feature))
        .unwrap_or(false)
}

/// Clear license (Tauri command)
#[tauri::command]
pub fn clear_stored_license() -> Result<(), LicenseError> {
    clear_license()
}

/// Check if license needs renewal (Tauri command)
#[tauri::command]
pub fn check_license_renewal_status() -> RenewalStatus {
    check_renewal_status()
}

/// Request license renewal from server (Tauri command - async)
#[tauri::command]
pub async fn request_license_renewal() -> Result<RenewalResponse, LicenseError> {
    request_renewal().await
}

/// Register license for renewal tracking (Tauri command - async)
#[tauri::command]
pub async fn register_license_for_renewal(license_key: String) -> Result<(), LicenseError> {
    register_for_renewal(&license_key).await
}

/// Import and activate license from a .key file path
#[tauri::command]
pub fn import_license_from_file(file_path: String) -> Result<LicensePayload, LicenseError> {
    let license_key = fs::read_to_string(&file_path)?;
    let license_key = license_key.trim();

    if license_key.is_empty() {
        return Err(LicenseError::InvalidFormat("License file is empty".into()));
    }

    if !license_key.starts_with("AURITY-") {
        return Err(LicenseError::InvalidFormat("Invalid license file: must start with AURITY-".into()));
    }

    activate_license(license_key)
}

/// Check if a valid license exists (for startup check)
#[tauri::command]
pub fn has_valid_license() -> bool {
    let status = get_license_status();
    status.is_valid
}
