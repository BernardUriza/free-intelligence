//! OS Keychain Storage — secure token persistence.
//!
//! Uses the `keyring` crate which maps to:
//!   - macOS: Keychain
//!   - Windows: Credential Manager
//!   - Linux: libsecret (GNOME Keyring / KWallet)
//!
//! Tokens are serialized as JSON before storage.

use keyring::Entry;

use super::{AuthError, AuthTokens, KEYRING_SERVICE, KEYRING_USER};

/// Store tokens securely in OS keychain.
pub(crate) fn store_tokens(tokens: &AuthTokens) -> Result<(), AuthError> {
    let entry = create_entry()?;

    let tokens_json = serde_json::to_string(tokens)
        .map_err(|e| AuthError::OAuthError(format!("Failed to serialize tokens: {}", e)))?;

    entry
        .set_password(&tokens_json)
        .map_err(|e| {
            AuthError::KeychainError(format!("Failed to store tokens in keychain: {}", e))
        })?;

    Ok(())
}

/// Get stored tokens from keychain.
/// Returns `None` if no tokens are stored.
#[tauri::command]
pub fn get_stored_tokens() -> Result<Option<AuthTokens>, AuthError> {
    let entry = create_entry()?;

    match entry.get_password() {
        Ok(tokens_json) => {
            let tokens: AuthTokens = serde_json::from_str(&tokens_json).map_err(|e| {
                AuthError::OAuthError(format!("Failed to parse stored tokens: {}", e))
            })?;
            Ok(Some(tokens))
        }
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(AuthError::KeychainError(format!(
            "Failed to get tokens from keychain: {}",
            e
        ))),
    }
}

/// Clear stored tokens (logout).
#[tauri::command]
pub fn clear_tokens() -> Result<(), AuthError> {
    let entry = create_entry()?;

    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()), // Already cleared
        Err(e) => Err(AuthError::KeychainError(format!(
            "Failed to clear tokens: {}",
            e
        ))),
    }
}

// ---------------------------------------------------------------------------
// Internal
// ---------------------------------------------------------------------------

/// Create a keyring entry with the standard service/user identifiers.
fn create_entry() -> Result<Entry, AuthError> {
    Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| AuthError::KeychainError(format!("Failed to create keyring entry: {}", e)))
}
