//! Auth0 OAuth 2.0 + PKCE implementation for Aurity Desktop
//!
//! This module handles the complete OAuth flow for desktop authentication:
//! 1. Generate PKCE verifier + challenge (RFC 7636)
//! 2. Open browser to Auth0 authorize URL
//! 3. Capture callback via deep link (aurity://callback?code=xxx)
//! 4. Exchange authorization code for tokens
//! 5. Store tokens securely in OS keychain (Keychain/Credential Manager/libsecret)
//!
//! Security considerations:
//! - PKCE prevents authorization code interception attacks
//! - State parameter prevents CSRF attacks
//! - Tokens stored in OS-level secure storage, not filesystem
//! - Refresh token rotation enabled for additional security

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use chrono::{DateTime, Utc};
use keyring::Entry;
use rand::Rng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::Mutex;
use tauri::{AppHandle, State};
use tauri_plugin_opener::OpenerExt;
use url::Url;

// Constants for Auth0 configuration
// These are read from environment at runtime via Tauri config
const KEYRING_SERVICE: &str = "io.aurity.desktop";
const KEYRING_USER: &str = "auth_tokens";

/// Stored tokens structure - serialized to JSON for keychain storage
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

/// Generate a cryptographically secure PKCE verifier and challenge
/// Returns (verifier, challenge) tuple
fn generate_pkce() -> (String, String) {
    // Generate 32 random bytes for verifier (results in 43 char base64)
    let verifier_bytes: [u8; 32] = rand::thread_rng().gen();
    let verifier = URL_SAFE_NO_PAD.encode(verifier_bytes);

    // SHA256 hash the verifier to create challenge
    let mut hasher = Sha256::new();
    hasher.update(verifier.as_bytes());
    let challenge = URL_SAFE_NO_PAD.encode(hasher.finalize());

    (verifier, challenge)
}

/// Generate random state parameter for CSRF protection
fn generate_state() -> String {
    let state_bytes: [u8; 16] = rand::thread_rng().gen();
    URL_SAFE_NO_PAD.encode(state_bytes)
}

/// Configure Auth0 settings - must be called before start_auth_flow
#[tauri::command]
pub fn configure_auth0(
    auth_state: State<'_, AuthState>,
    domain: String,
    client_id: String,
    audience: String,
) -> Result<(), String> {
    let config = Auth0Config {
        domain,
        client_id,
        audience,
        redirect_uri: "aurity://callback".to_string(),
    };

    let mut config_lock = auth_state
        .config
        .lock()
        .map_err(|e| format!("Failed to acquire config lock: {}", e))?;
    *config_lock = Some(config);

    Ok(())
}

/// Start OAuth flow - opens browser to Auth0 authorize URL
/// Returns the state parameter for verification
#[tauri::command]
pub async fn start_auth_flow(
    app: AppHandle,
    auth_state: State<'_, AuthState>,
) -> Result<String, String> {
    // Get Auth0 config
    let config = {
        let config_lock = auth_state
            .config
            .lock()
            .map_err(|e| format!("Failed to acquire config lock: {}", e))?;
        config_lock
            .clone()
            .ok_or("Auth0 not configured. Call configure_auth0 first.")?
    };

    // Generate PKCE parameters
    let (verifier, challenge) = generate_pkce();
    let state = generate_state();

    // Store PKCE state for later verification
    {
        let mut pkce_lock = auth_state
            .pkce
            .lock()
            .map_err(|e| format!("Failed to acquire PKCE lock: {}", e))?;
        *pkce_lock = Some(PkceState {
            verifier,
            state: state.clone(),
            created_at: Utc::now(),
        });
    }

    // Build authorize URL
    let auth_url = format!(
        "https://{}/authorize?\
         response_type=code&\
         client_id={}&\
         redirect_uri={}&\
         scope={}&\
         audience={}&\
         state={}&\
         code_challenge={}&\
         code_challenge_method=S256",
        config.domain,
        urlencoding::encode(&config.client_id),
        urlencoding::encode(&config.redirect_uri),
        urlencoding::encode("openid profile email offline_access"),
        urlencoding::encode(&config.audience),
        urlencoding::encode(&state),
        urlencoding::encode(&challenge)
    );

    // Open in default browser using tauri-plugin-opener
    app.opener()
        .open_url(&auth_url, None::<&str>)
        .map_err(|e| format!("Failed to open browser: {}", e))?;

    Ok(state)
}

/// Handle OAuth callback from deep link
/// Extracts code, validates state, exchanges for tokens, stores in keychain
#[tauri::command]
pub async fn handle_auth_callback(
    auth_state: State<'_, AuthState>,
    callback_url: String,
) -> Result<AuthTokens, String> {
    // Parse callback URL
    let parsed = Url::parse(&callback_url).map_err(|e| format!("Invalid callback URL: {}", e))?;

    let params: HashMap<_, _> = parsed.query_pairs().collect();

    // Check for error response from Auth0
    if let Some(error) = params.get("error") {
        let desc = params
            .get("error_description")
            .map(|s| s.to_string())
            .unwrap_or_else(|| "Unknown error".to_string());
        return Err(format!("Auth0 error: {} - {}", error, desc));
    }

    // Validate state parameter (CSRF protection)
    let returned_state = params
        .get("state")
        .ok_or("Missing state parameter in callback")?;

    let (verifier, config) = {
        let pkce_lock = auth_state
            .pkce
            .lock()
            .map_err(|e| format!("Failed to acquire PKCE lock: {}", e))?;
        let pkce_state = pkce_lock.as_ref().ok_or("No pending auth flow")?;

        if *returned_state != pkce_state.state {
            return Err("State mismatch - possible CSRF attack".to_string());
        }

        // Check if PKCE state is too old (5 minutes max)
        let age = Utc::now() - pkce_state.created_at;
        if age.num_minutes() > 5 {
            return Err("Auth flow expired. Please try again.".to_string());
        }

        let config_lock = auth_state
            .config
            .lock()
            .map_err(|e| format!("Failed to acquire config lock: {}", e))?;
        let config = config_lock.clone().ok_or("Auth0 not configured")?;

        (pkce_state.verifier.clone(), config)
    };

    // Get authorization code
    let code = params
        .get("code")
        .ok_or("Missing authorization code in callback")?;

    // Exchange code for tokens
    let tokens = exchange_code_for_tokens(&code, &verifier, &config).await?;

    // Clear PKCE state (one-time use)
    {
        let mut pkce_lock = auth_state
            .pkce
            .lock()
            .map_err(|e| format!("Failed to acquire PKCE lock: {}", e))?;
        *pkce_lock = None;
    }

    // Store tokens in keychain
    store_tokens_in_keychain(&tokens)?;

    Ok(tokens)
}

/// Exchange authorization code for tokens via Auth0 token endpoint
async fn exchange_code_for_tokens(
    code: &str,
    verifier: &str,
    config: &Auth0Config,
) -> Result<AuthTokens, String> {
    let client = reqwest::Client::new();
    let token_url = format!("https://{}/oauth/token", config.domain);

    let params = [
        ("grant_type", "authorization_code"),
        ("client_id", &config.client_id),
        ("code_verifier", verifier),
        ("code", code),
        ("redirect_uri", &config.redirect_uri),
    ];

    let response = client
        .post(&token_url)
        .form(&params)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("Token request failed: {}", e))?;

    if !response.status().is_success() {
        let status = response.status();
        // Consume body but don't log it (might contain sensitive info)
        let _error_body = response.text().await.unwrap_or_default();
        return Err(format!("Token exchange failed with status {}", status));
    }

    #[derive(Deserialize)]
    struct TokenResponse {
        access_token: String,
        refresh_token: Option<String>,
        id_token: Option<String>,
        expires_in: i64,
        token_type: String,
    }

    let token_response: TokenResponse = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse token response: {}", e))?;

    let expires_at = Utc::now().timestamp() + token_response.expires_in;

    Ok(AuthTokens {
        access_token: token_response.access_token,
        refresh_token: token_response.refresh_token,
        id_token: token_response.id_token,
        expires_at,
        token_type: token_response.token_type,
    })
}

/// Store tokens securely in OS keychain
fn store_tokens_in_keychain(tokens: &AuthTokens) -> Result<(), String> {
    let entry = Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    let tokens_json =
        serde_json::to_string(tokens).map_err(|e| format!("Failed to serialize tokens: {}", e))?;

    entry
        .set_password(&tokens_json)
        .map_err(|e| format!("Failed to store tokens in keychain: {}", e))?;

    Ok(())
}

/// Get stored tokens from keychain
#[tauri::command]
pub fn get_stored_tokens() -> Result<Option<AuthTokens>, String> {
    let entry = Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    match entry.get_password() {
        Ok(tokens_json) => {
            let tokens: AuthTokens = serde_json::from_str(&tokens_json)
                .map_err(|e| format!("Failed to parse stored tokens: {}", e))?;
            Ok(Some(tokens))
        }
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(format!("Failed to get tokens from keychain: {}", e)),
    }
}

/// Refresh access token using refresh token
#[tauri::command]
pub async fn refresh_tokens(auth_state: State<'_, AuthState>) -> Result<AuthTokens, String> {
    // Get current tokens
    let current_tokens = get_stored_tokens()?.ok_or("No stored tokens to refresh")?;

    let refresh_token = current_tokens
        .refresh_token
        .ok_or("No refresh token available")?;

    // Get Auth0 config
    let config = {
        let config_lock = auth_state
            .config
            .lock()
            .map_err(|e| format!("Failed to acquire config lock: {}", e))?;
        config_lock.clone().ok_or("Auth0 not configured")?
    };

    let client = reqwest::Client::new();
    let token_url = format!("https://{}/oauth/token", config.domain);

    let params = [
        ("grant_type", "refresh_token"),
        ("client_id", &config.client_id),
        ("refresh_token", &refresh_token),
    ];

    let response = client
        .post(&token_url)
        .form(&params)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("Refresh request failed: {}", e))?;

    if !response.status().is_success() {
        // Refresh token might be revoked - clear stored tokens
        let _ = clear_tokens();
        return Err("Refresh token revoked - re-authentication required".to_string());
    }

    #[derive(Deserialize)]
    struct RefreshResponse {
        access_token: String,
        refresh_token: Option<String>, // New refresh token if rotation enabled
        id_token: Option<String>,
        expires_in: i64,
        token_type: String,
    }

    let token_response: RefreshResponse = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse refresh response: {}", e))?;

    let expires_at = Utc::now().timestamp() + token_response.expires_in;

    let new_tokens = AuthTokens {
        access_token: token_response.access_token,
        // Use new refresh token if provided (rotation), otherwise keep old
        refresh_token: token_response.refresh_token.or(Some(refresh_token)),
        id_token: token_response.id_token.or(current_tokens.id_token),
        expires_at,
        token_type: token_response.token_type,
    };

    // Store updated tokens
    store_tokens_in_keychain(&new_tokens)?;

    Ok(new_tokens)
}

/// Clear stored tokens (logout)
#[tauri::command]
pub fn clear_tokens() -> Result<(), String> {
    let entry = Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()), // Already cleared
        Err(e) => Err(format!("Failed to clear tokens: {}", e)),
    }
}

/// Check if tokens are expired (with 60s buffer)
#[tauri::command]
pub fn is_token_expired() -> Result<bool, String> {
    match get_stored_tokens()? {
        Some(tokens) => {
            let now = Utc::now().timestamp();
            // Consider expired 60 seconds before actual expiry (buffer for network latency)
            Ok(now >= tokens.expires_at - 60)
        }
        None => Ok(true), // No tokens = expired
    }
}

/// Get token expiration timestamp
#[tauri::command]
pub fn get_token_expiry() -> Result<Option<i64>, String> {
    match get_stored_tokens()? {
        Some(tokens) => Ok(Some(tokens.expires_at)),
        None => Ok(None),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_pkce() {
        let (verifier, challenge) = generate_pkce();

        // Verifier should be 43 characters (32 bytes base64url encoded)
        assert_eq!(verifier.len(), 43);

        // Challenge should also be 43 characters (SHA256 = 32 bytes base64url encoded)
        assert_eq!(challenge.len(), 43);

        // Verifier and challenge should be different
        assert_ne!(verifier, challenge);
    }

    #[test]
    fn test_generate_state() {
        let state = generate_state();

        // State should be 22 characters (16 bytes base64url encoded)
        assert_eq!(state.len(), 22);

        // Two calls should produce different states
        let state2 = generate_state();
        assert_ne!(state, state2);
    }
}
