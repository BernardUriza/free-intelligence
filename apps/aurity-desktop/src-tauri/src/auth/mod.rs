//! Auth0 OAuth 2.0 + PKCE implementation for Aurity Desktop
//!
//! Handles the complete OAuth flow for desktop authentication:
//!   1. Generate PKCE verifier + challenge (RFC 7636)
//!   2. Open browser to Auth0 authorize URL
//!   3. Capture callback via deep link (aurity://callback?code=xxx)
//!   4. Exchange authorization code for tokens
//!   5. Store tokens securely in OS keychain
//!
//! Module structure (SRP):
//!   pkce.rs     — PKCE verifier/challenge and state generation
//!   keychain.rs — OS keychain storage (Keychain/Credential Manager/libsecret)
//!   flow.rs     — OAuth authorize, callback, and code exchange
//!   tokens.rs   — Token refresh, expiry checks
//!
//! Security:
//!   - PKCE prevents authorization code interception attacks
//!   - State parameter prevents CSRF attacks
//!   - Tokens stored in OS-level secure storage, not filesystem
//!   - Refresh token rotation enabled for additional security

pub mod flow;
pub mod keychain;
pub mod pkce;
pub mod tokens;

use chrono::DateTime;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

// =============================================================================
// CONSTANTS
// =============================================================================

/// Keyring service identifier (matches bundle identifier)
pub(crate) const KEYRING_SERVICE: &str = "io.aurity.desktop";

/// Keyring user key for token storage
pub(crate) const KEYRING_USER: &str = "auth_tokens";

/// Maximum age of a PKCE flow before it expires (minutes)
pub(crate) const PKCE_MAX_AGE_MINUTES: i64 = 5;

/// HTTP timeout for Auth0 token endpoint requests (seconds)
pub(crate) const TOKEN_REQUEST_TIMEOUT_SECS: u64 = 30;

/// Deep link redirect URI for OAuth callback
pub(crate) const REDIRECT_URI: &str = "aurity://callback";

/// Buffer (seconds) before actual expiry to consider token expired
pub(crate) const TOKEN_EXPIRY_BUFFER_SECS: i64 = 60;

// =============================================================================
// TYPES
// =============================================================================

/// Auth errors for Tauri commands
#[derive(Debug, thiserror::Error, Serialize)]
pub enum AuthError {
    #[error("Not configured: {0}")]
    NotConfigured(String),
    #[error("OAuth error: {0}")]
    OAuthError(String),
    #[error("Keychain error: {0}")]
    KeychainError(String),
    #[error("Network error: {0}")]
    Network(String),
    #[error("CSRF validation failed: {0}")]
    CsrfError(String),
}

/// Stored tokens — serialized to JSON for keychain storage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub id_token: Option<String>,
    pub expires_at: i64, // Unix timestamp (seconds)
    pub token_type: String,
}

/// PKCE state stored during auth flow (in-memory only)
#[derive(Debug, Clone)]
pub struct PkceState {
    pub verifier: String,
    pub state: String,
    pub created_at: DateTime<Utc>,
}

/// Auth0 configuration passed from frontend
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Auth0Config {
    pub domain: String,
    pub client_id: String,
    pub audience: String,
    pub redirect_uri: String,
}

/// Global auth state managed by Tauri
pub struct AuthState {
    pub pkce: Mutex<Option<PkceState>>,
    pub config: Mutex<Option<Auth0Config>>,
}

impl Default for AuthState {
    fn default() -> Self {
        Self {
            pkce: Mutex::new(None),
            config: Mutex::new(None),
        }
    }
}

// =============================================================================
// RE-EXPORTS (Tauri commands)
// =============================================================================

pub use flow::{configure_auth0, handle_auth_callback, start_auth_flow};
pub use keychain::{clear_tokens, get_stored_tokens};
pub use tokens::{get_token_expiry, is_token_expired, refresh_tokens};
