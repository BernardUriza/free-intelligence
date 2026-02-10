use chrono::Utc;
use log::info;
use std::fs;
use std::path::PathBuf;

use super::crypto::validate_license;
use super::types::{
    Auth0Config, LicenseError, LicensePayload, LicenseStatus, LicenseValidationResult,
    StoredLicense,
};

/// Get the license storage path
pub fn get_license_path() -> Result<PathBuf, LicenseError> {
    let home = dirs::home_dir().ok_or(LicenseError::Storage("Could not find home directory".into()))?;
    Ok(home.join(".aurity").join("storage").join("license.json"))
}

/// Activate a license key (store to disk)
pub fn activate_license(license_key: &str) -> Result<LicensePayload, LicenseError> {
    let result = validate_license(license_key);

    if !result.is_valid {
        return Err(LicenseError::InvalidFormat(result.message));
    }

    let payload = result.payload.ok_or(LicenseError::InvalidFormat("No payload in valid license".into()))?;

    let license_path = get_license_path()?;
    if let Some(parent) = license_path.parent() {
        fs::create_dir_all(parent)?;
    }

    let stored = StoredLicense {
        license_key: license_key.to_string(),
        activated_at: Utc::now().to_rfc3339(),
        payload: payload.clone(),
    };

    let json = serde_json::to_string_pretty(&stored)?;
    fs::write(&license_path, json)?;

    info!("License activated: {}", payload.license_id);

    Ok(payload)
}

/// Get stored license status
pub fn get_license_status() -> LicenseValidationResult {
    let license_path = match get_license_path() {
        Ok(p) => p,
        Err(e) => {
            return LicenseValidationResult {
                status: LicenseStatus::InvalidFormat.as_str().to_string(),
                is_valid: false,
                message: e.to_string(),
                days_remaining: None,
                payload: None,
            };
        }
    };

    if !license_path.exists() {
        return LicenseValidationResult {
            status: LicenseStatus::NotActivated.as_str().to_string(),
            is_valid: false,
            message: "No license activated".to_string(),
            days_remaining: None,
            payload: None,
        };
    }

    let content = match fs::read_to_string(&license_path) {
        Ok(c) => c,
        Err(e) => {
            return LicenseValidationResult {
                status: LicenseStatus::InvalidFormat.as_str().to_string(),
                is_valid: false,
                message: format!("Failed to read license file: {}", e),
                days_remaining: None,
                payload: None,
            };
        }
    };

    let stored: StoredLicense = match serde_json::from_str(&content) {
        Ok(s) => s,
        Err(e) => {
            return LicenseValidationResult {
                status: LicenseStatus::InvalidFormat.as_str().to_string(),
                is_valid: false,
                message: format!("Invalid license file format: {}", e),
                days_remaining: None,
                payload: None,
            };
        }
    };

    validate_license(&stored.license_key)
}

/// Get Auth0 configuration from stored license
pub fn get_auth0_config() -> Result<Auth0Config, LicenseError> {
    let status = get_license_status();

    if !status.is_valid {
        return Err(LicenseError::NotActivated(status.message));
    }

    let payload = status.payload.ok_or(LicenseError::NotActivated("No payload in valid license".into()))?;

    Ok(Auth0Config {
        domain: payload.auth0_domain,
        client_id: payload.auth0_client_id,
        audience: payload.auth0_audience,
    })
}

/// Clear stored license (for testing/logout)
pub fn clear_license() -> Result<(), LicenseError> {
    let license_path = get_license_path()?;

    if license_path.exists() {
        fs::remove_file(&license_path)?;
    }

    Ok(())
}
