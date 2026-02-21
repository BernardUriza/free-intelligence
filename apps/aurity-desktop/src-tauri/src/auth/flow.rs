//! OAuth Flow — configure, authorize, callback, and code exchange.
//!
//! Implements the Authorization Code + PKCE flow:
//!   1. configure_auth0()       → store Auth0 domain/clientId/audience
//!   2. start_auth_flow()       → generate PKCE, open browser
//!   3. handle_auth_callback()  → validate state, exchange code, store tokens

use chrono::Utc;
use serde::Deserialize;
use std::collections::HashMap;
use tauri::{AppHandle, State};
use tauri_plugin_opener::OpenerExt;
use url::Url;

use super::keychain;
use super::pkce;
use super::{
    Auth0Config, AuthError, AuthState, AuthTokens, PkceState, PKCE_MAX_AGE_MINUTES, REDIRECT_URI,
    TOKEN_REQUEST_TIMEOUT_SECS,
};

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Configure Auth0 settings — must be called before `start_auth_flow`.
#[tauri::command]
pub fn configure_auth0(
    auth_state: State<'_, AuthState>,
    domain: String,
    client_id: String,
    audience: String,
) -> Result<(), AuthError> {
    let config = Auth0Config {
        domain,
        client_id,
        audience,
        redirect_uri: REDIRECT_URI.to_string(),
    };

    let mut config_lock = auth_state
        .config
        .lock()
        .map_err(|e| AuthError::OAuthError(format!("Failed to acquire config lock: {}", e)))?;
    *config_lock = Some(config);

    Ok(())
}

/// Start OAuth flow — opens browser to Auth0 authorize URL.
/// Returns the state parameter for verification.
#[tauri::command]
pub async fn start_auth_flow(
    app: AppHandle,
    auth_state: State<'_, AuthState>,
) -> Result<String, AuthError> {
    let config = get_config(&auth_state)?;

    // Generate PKCE parameters
    let (verifier, challenge) = pkce::generate_pkce();
    let state = pkce::generate_state();

    // Store PKCE state for later verification
    store_pkce_state(&auth_state, &verifier, &state)?;

    // Build authorize URL
    let auth_url = build_authorize_url(&config, &state, &challenge);

    // Open in default browser
    app.opener()
        .open_url(&auth_url, None::<&str>)
        .map_err(|e| AuthError::OAuthError(format!("Failed to open browser: {}", e)))?;

    Ok(state)
}

/// Handle OAuth callback from deep link.
/// Validates state (CSRF), exchanges code for tokens, stores in keychain.
#[tauri::command]
pub async fn handle_auth_callback(
    auth_state: State<'_, AuthState>,
    callback_url: String,
) -> Result<AuthTokens, AuthError> {
    let parsed = Url::parse(&callback_url)
        .map_err(|e| AuthError::OAuthError(format!("Invalid callback URL: {}", e)))?;

    let params: HashMap<_, _> = parsed.query_pairs().collect();

    // Check for error response from Auth0
    check_auth0_error(&params)?;

    // Validate state parameter (CSRF protection)
    let returned_state = params
        .get("state")
        .ok_or(AuthError::CsrfError("Missing state parameter in callback".into()))?;

    // Extract and validate PKCE verifier
    let verifier = validate_and_consume_pkce(&auth_state, returned_state)?;

    // Get config
    let config = get_config(&auth_state)?;

    // Get authorization code
    let code = params
        .get("code")
        .ok_or(AuthError::OAuthError("Missing authorization code in callback".into()))?;

    // Exchange code for tokens
    let tokens = exchange_code_for_tokens(code, &verifier, &config).await?;

    // Store tokens in keychain
    keychain::store_tokens(&tokens)?;

    Ok(tokens)
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/// Get Auth0 config from state, or error if not configured.
pub(crate) fn get_config(auth_state: &AuthState) -> Result<Auth0Config, AuthError> {
    let config_lock = auth_state
        .config
        .lock()
        .map_err(|e| AuthError::OAuthError(format!("Failed to acquire config lock: {}", e)))?;
    config_lock
        .clone()
        .ok_or(AuthError::NotConfigured("Auth0 not configured. Call configure_auth0 first.".into()))
}

/// Store PKCE state in auth_state for later verification.
fn store_pkce_state(
    auth_state: &AuthState,
    verifier: &str,
    state: &str,
) -> Result<(), AuthError> {
    let mut pkce_lock = auth_state
        .pkce
        .lock()
        .map_err(|e| AuthError::OAuthError(format!("Failed to acquire PKCE lock: {}", e)))?;
    *pkce_lock = Some(PkceState {
        verifier: verifier.to_string(),
        state: state.to_string(),
        created_at: Utc::now(),
    });
    Ok(())
}

/// Build the Auth0 authorize URL with PKCE challenge.
fn build_authorize_url(config: &Auth0Config, state: &str, challenge: &str) -> String {
    format!(
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
        urlencoding::encode(state),
        urlencoding::encode(challenge),
    )
}

/// Check if Auth0 returned an error in the callback params.
fn check_auth0_error(params: &HashMap<std::borrow::Cow<str>, std::borrow::Cow<str>>) -> Result<(), AuthError> {
    if let Some(error) = params.get("error") {
        let desc = params
            .get("error_description")
            .map(|s| s.to_string())
            .unwrap_or_else(|| "Unknown error".to_string());
        return Err(AuthError::OAuthError(format!(
            "Auth0 error: {} - {}",
            error, desc
        )));
    }
    Ok(())
}

/// Validate the returned state against stored PKCE, check age, extract verifier,
/// and clear the one-time PKCE state.
fn validate_and_consume_pkce(
    auth_state: &AuthState,
    returned_state: &str,
) -> Result<String, AuthError> {
    let verifier = {
        let pkce_lock = auth_state
            .pkce
            .lock()
            .map_err(|e| AuthError::OAuthError(format!("Failed to acquire PKCE lock: {}", e)))?;
        let pkce_state = pkce_lock
            .as_ref()
            .ok_or(AuthError::OAuthError("No pending auth flow".into()))?;

        if returned_state != pkce_state.state {
            return Err(AuthError::CsrfError(
                "State mismatch - possible CSRF attack".into(),
            ));
        }

        let age = Utc::now() - pkce_state.created_at;
        if age.num_minutes() > PKCE_MAX_AGE_MINUTES {
            return Err(AuthError::OAuthError(
                "Auth flow expired. Please try again.".into(),
            ));
        }

        pkce_state.verifier.clone()
    }; // pkce_lock dropped

    // Clear one-time PKCE state
    {
        let mut pkce_lock = auth_state
            .pkce
            .lock()
            .map_err(|e| AuthError::OAuthError(format!("Failed to acquire PKCE lock: {}", e)))?;
        *pkce_lock = None;
    }

    Ok(verifier)
}

/// Exchange authorization code for tokens via Auth0 token endpoint.
pub(crate) async fn exchange_code_for_tokens(
    code: &str,
    verifier: &str,
    config: &Auth0Config,
) -> Result<AuthTokens, AuthError> {
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
        .timeout(std::time::Duration::from_secs(TOKEN_REQUEST_TIMEOUT_SECS))
        .send()
        .await
        .map_err(|e| AuthError::Network(format!("Token request failed: {}", e)))?;

    if !response.status().is_success() {
        let status = response.status();
        // Consume body but don't log it (might contain sensitive info)
        let _error_body = response.text().await.unwrap_or_default();
        return Err(AuthError::OAuthError(format!(
            "Token exchange failed with status {}",
            status
        )));
    }

    parse_token_response(response).await
}

/// Parse the JSON token response from Auth0.
async fn parse_token_response(response: reqwest::Response) -> Result<AuthTokens, AuthError> {
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
        .map_err(|e| AuthError::OAuthError(format!("Failed to parse token response: {}", e)))?;

    let expires_at = Utc::now().timestamp() + token_response.expires_in;

    Ok(AuthTokens {
        access_token: token_response.access_token,
        refresh_token: token_response.refresh_token,
        id_token: token_response.id_token,
        expires_at,
        token_type: token_response.token_type,
    })
}
