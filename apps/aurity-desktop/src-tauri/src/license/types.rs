use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// License errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
pub enum LicenseError {
    #[error("Invalid license format: {0}")]
    InvalidFormat(String),
    #[error("Invalid signature: {0}")]
    InvalidSignature(String),
    #[error("Not activated: {0}")]
    NotActivated(String),
    #[error("Storage error: {0}")]
    Storage(String),
    #[error("Network error: {0}")]
    Network(String),
}

impl From<std::io::Error> for LicenseError {
    fn from(e: std::io::Error) -> Self {
        LicenseError::Storage(e.to_string())
    }
}

impl From<serde_json::Error> for LicenseError {
    fn from(e: serde_json::Error) -> Self {
        LicenseError::InvalidFormat(e.to_string())
    }
}

/// License payload structure (matches Python generator)
/// NOTE: Clinics are NOT embedded in license. The license sets max_clinics limit,
/// and actual clinics are created via API after license activation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicensePayload {
    pub license_id: String,
    pub auth0_domain: String,
    pub auth0_client_id: String,
    pub auth0_audience: String,
    pub max_clinics: u32,
    pub license_holder: String,
    pub features: Vec<String>,
    pub issued_at: String,
    pub expires_at: String,
    pub version: String,
}

impl LicensePayload {
    /// Check if the license has expired
    pub fn is_expired(&self) -> bool {
        if self.expires_at.is_empty() {
            return false; // Perpetual license
        }

        match DateTime::parse_from_rfc3339(&self.expires_at) {
            Ok(expires) => Utc::now() > expires,
            Err(_) => {
                // Try ISO 8601 format with timezone
                if let Ok(expires) =
                    DateTime::parse_from_str(&self.expires_at, "%Y-%m-%dT%H:%M:%S%.f%:z")
                {
                    Utc::now() > expires
                } else {
                    true // Invalid date = expired
                }
            }
        }
    }

    /// Days remaining until expiration (negative if expired)
    pub fn days_remaining(&self) -> Option<i64> {
        if self.expires_at.is_empty() {
            return None; // Perpetual license
        }

        let expires = DateTime::parse_from_rfc3339(&self.expires_at)
            .or_else(|_| DateTime::parse_from_str(&self.expires_at, "%Y-%m-%dT%H:%M:%S%.f%:z"))
            .ok()?;

        let duration = expires.signed_duration_since(Utc::now());
        Some(duration.num_days())
    }

    /// Check if a feature is enabled
    pub fn has_feature(&self, feature: &str) -> bool {
        self.features.iter().any(|f| f == feature)
    }
}

/// License validation status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LicenseStatus {
    Valid,
    Expired,
    InvalidSignature,
    InvalidFormat,
    NotActivated,
}

impl LicenseStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            LicenseStatus::Valid => "valid",
            LicenseStatus::Expired => "expired",
            LicenseStatus::InvalidSignature => "invalid_signature",
            LicenseStatus::InvalidFormat => "invalid_format",
            LicenseStatus::NotActivated => "not_activated",
        }
    }
}

/// Result of license validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseValidationResult {
    pub status: String,
    pub is_valid: bool,
    pub message: String,
    pub days_remaining: Option<i64>,
    pub payload: Option<LicensePayload>,
}

/// Auth0 configuration extracted from license
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Auth0Config {
    pub domain: String,
    pub client_id: String,
    pub audience: String,
}

/// Stored license data (saved to disk)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoredLicense {
    pub license_key: String,
    pub activated_at: String,
    pub payload: LicensePayload,
}

/// Decoded license data (payload, original payload bytes, signature bytes)
pub struct DecodedLicense {
    pub payload: LicensePayload,
    pub payload_bytes: Vec<u8>,
    pub signature_bytes: Vec<u8>,
}

/// Renewal request sent to server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RenewalRequest {
    pub license_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub machine_fingerprint: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub current_expires_at: Option<String>,
}

/// Renewal response from server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RenewalResponse {
    pub renewed: bool,
    pub reason: Option<String>,
    pub new_expires_at: Option<String>,
    pub new_license_key: Option<String>,
    pub renewal_url: Option<String>,
    pub message: String,
}

/// License renewal status for frontend
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RenewalStatus {
    pub needs_renewal: bool,
    pub days_until_expiry: Option<i64>,
    pub renewal_url: Option<String>,
    pub warning_message: Option<String>,
}
