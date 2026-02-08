use log::info;

use super::storage::{activate_license, get_license_status};
use super::types::{LicenseError, RenewalRequest, RenewalResponse, RenewalStatus};

/// Renewal API base URL (production)
const RENEWAL_API_BASE: &str = "https://app.aurity.io/api";

/// Get machine fingerprint for license binding (simplified)
fn get_machine_fingerprint() -> Option<String> {
    let hostname = hostname::get().ok()?.into_string().ok()?;

    #[cfg(target_os = "macos")]
    let os_id = "macos";
    #[cfg(target_os = "windows")]
    let os_id = "windows";
    #[cfg(target_os = "linux")]
    let os_id = "linux";
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    let os_id = "unknown";

    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    format!("{}-{}", hostname, os_id).hash(&mut hasher);
    Some(format!("{:016x}", hasher.finish()))
}

/// Check if license needs renewal (called periodically)
pub fn check_renewal_status() -> RenewalStatus {
    let status = get_license_status();

    if !status.is_valid && status.status != "expired" {
        return RenewalStatus {
            needs_renewal: false,
            days_until_expiry: None,
            renewal_url: None,
            warning_message: Some("License not activated".to_string()),
        };
    }

    let days = status.days_remaining.unwrap_or(0);

    let warning_message = if days < 0 {
        Some("Your license has expired. Please renew to continue using Aurity.".to_string())
    } else if days <= 7 {
        Some(format!(
            "Your license expires in {} days. Please renew soon.",
            days
        ))
    } else if days <= 30 {
        Some(format!("Your license expires in {} days.", days))
    } else {
        None
    };

    let license_id = status
        .payload
        .as_ref()
        .map(|p| p.license_id.clone())
        .unwrap_or_default();

    RenewalStatus {
        needs_renewal: days <= 30,
        days_until_expiry: status.days_remaining,
        renewal_url: if days <= 30 {
            Some(format!(
                "https://app.aurity.io/renew?license={}",
                license_id
            ))
        } else {
            None
        },
        warning_message,
    }
}

/// Request license renewal from server (async HTTP call)
pub async fn request_renewal() -> Result<RenewalResponse, LicenseError> {
    let status = get_license_status();

    let payload = status.payload.ok_or(LicenseError::NotActivated("No valid license to renew".into()))?;

    let request = RenewalRequest {
        license_id: payload.license_id.clone(),
        machine_fingerprint: get_machine_fingerprint(),
        current_expires_at: Some(payload.expires_at.clone()),
    };

    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/licenses/renew", RENEWAL_API_BASE))
        .json(&request)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| LicenseError::Network(format!("Network error: {}", e)))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(LicenseError::Network(format!("Server error {}: {}", status, body)));
    }

    let renewal: RenewalResponse = response
        .json()
        .await
        .map_err(|e| LicenseError::Network(format!("Invalid response: {}", e)))?;

    if renewal.renewed {
        if let Some(ref new_key) = renewal.new_license_key {
            activate_license(new_key)?;
            info!("License renewed successfully!");
        }
    }

    Ok(renewal)
}

/// Register license for renewal service
pub async fn register_for_renewal(license_key: &str) -> Result<(), LicenseError> {
    let client = reqwest::Client::new();

    let response = client
        .post(format!("{}/licenses/register", RENEWAL_API_BASE))
        .query(&[("license_key", license_key)])
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| LicenseError::Network(format!("Network error: {}", e)))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(LicenseError::Network(format!("Registration failed {}: {}", status, body)));
    }

    info!("License registered for renewal service");
    Ok(())
}
