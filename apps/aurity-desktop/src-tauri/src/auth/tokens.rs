//! Token Management — refresh, expiry checks.

use chrono::Utc;
use serde::Deserialize;
use tauri::State;

use super::flow;
use super::keychain;
use super::{AuthError, AuthState, AuthTokens, TOKEN_EXPIRY_BUFFER_SECS, TOKEN_REQUEST_TIMEOUT_SECS};

/// Refresh access token using refresh token.
/// If refresh token rotation is enabled, the new refresh token is stored.
#[tauri::command]
pub async fn refresh_tokens(auth_state: State<'_, AuthState>) -> Result<AuthTokens, AuthError> {
    let current_tokens = keychain::get_stored_tokens()?
        .ok_or(AuthError::OAuthError("No stored tokens to refresh".into()))?;

    let refresh_token = current_tokens
        .refresh_token
        .clone()
        .ok_or(AuthError::OAuthError("No refresh token available".into()))?;

    let config = flow::get_config(&auth_state)?;

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
        .timeout(std::time::Duration::from_secs(TOKEN_REQUEST_TIMEOUT_SECS))
        .send()
        .await
        .map_err(|e| AuthError::Network(format!("Refresh request failed: {}", e)))?;

    if !response.status().is_success() {
        // Refresh token might be revoked — clear stored tokens
        let _ = keychain::clear_tokens();
        return Err(AuthError::OAuthError(
            "Refresh token revoked - re-authentication required".into(),
        ));
    }

    let new_tokens = parse_refresh_response(response, &refresh_token, &current_tokens).await?;

    keychain::store_tokens(&new_tokens)?;

    Ok(new_tokens)
}

/// Check if tokens are expired (with buffer for network latency).
#[tauri::command]
pub fn is_token_expired() -> Result<bool, AuthError> {
    match keychain::get_stored_tokens()? {
        Some(tokens) => {
            let now = Utc::now().timestamp();
            Ok(now >= tokens.expires_at - TOKEN_EXPIRY_BUFFER_SECS)
        }
        None => Ok(true), // No tokens = expired
    }
}

/// Get token expiration timestamp.
#[tauri::command]
pub fn get_token_expiry() -> Result<Option<i64>, AuthError> {
    match keychain::get_stored_tokens()? {
        Some(tokens) => Ok(Some(tokens.expires_at)),
        None => Ok(None),
    }
}

// ---------------------------------------------------------------------------
// Internal
// ---------------------------------------------------------------------------

/// Parse the refresh token response and merge with existing tokens.
async fn parse_refresh_response(
    response: reqwest::Response,
    old_refresh_token: &str,
    current_tokens: &AuthTokens,
) -> Result<AuthTokens, AuthError> {
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
        .map_err(|e| AuthError::OAuthError(format!("Failed to parse refresh response: {}", e)))?;

    let expires_at = Utc::now().timestamp() + token_response.expires_in;

    Ok(AuthTokens {
        access_token: token_response.access_token,
        // Use new refresh token if provided (rotation), otherwise keep old
        refresh_token: token_response
            .refresh_token
            .or(Some(old_refresh_token.to_string())),
        id_token: token_response.id_token.or(current_tokens.id_token.clone()),
        expires_at,
        token_type: token_response.token_type,
    })
}
