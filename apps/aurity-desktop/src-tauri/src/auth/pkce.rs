//! PKCE (Proof Key for Code Exchange) generation — RFC 7636.
//!
//! Generates cryptographically secure verifier/challenge pairs
//! and random state parameters for CSRF protection.

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use rand::Rng;
use sha2::{Digest, Sha256};

/// Generate a PKCE verifier and S256 challenge.
///
/// Returns `(verifier, challenge)`:
///   - verifier: 43-char base64url string (32 random bytes)
///   - challenge: 43-char base64url string (SHA-256 of verifier)
pub(crate) fn generate_pkce() -> (String, String) {
    let verifier_bytes: [u8; 32] = rand::thread_rng().gen();
    let verifier = URL_SAFE_NO_PAD.encode(verifier_bytes);

    let mut hasher = Sha256::new();
    hasher.update(verifier.as_bytes());
    let challenge = URL_SAFE_NO_PAD.encode(hasher.finalize());

    (verifier, challenge)
}

/// Generate a random state parameter for CSRF protection.
///
/// Returns a 22-char base64url string (16 random bytes).
pub(crate) fn generate_state() -> String {
    let state_bytes: [u8; 16] = rand::thread_rng().gen();
    URL_SAFE_NO_PAD.encode(state_bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_pkce() {
        let (verifier, challenge) = generate_pkce();

        // 32 bytes → 43 chars base64url
        assert_eq!(verifier.len(), 43);
        assert_eq!(challenge.len(), 43);

        // Verifier and challenge must differ
        assert_ne!(verifier, challenge);
    }

    #[test]
    fn test_generate_pkce_deterministic_challenge() {
        // Same verifier should always produce the same challenge
        let (verifier, challenge1) = generate_pkce();

        let mut hasher = Sha256::new();
        hasher.update(verifier.as_bytes());
        let challenge2 = URL_SAFE_NO_PAD.encode(hasher.finalize());

        assert_eq!(challenge1, challenge2);
    }

    #[test]
    fn test_generate_state() {
        let state = generate_state();

        // 16 bytes → 22 chars base64url
        assert_eq!(state.len(), 22);
    }

    #[test]
    fn test_generate_state_unique() {
        let state1 = generate_state();
        let state2 = generate_state();
        assert_ne!(state1, state2);
    }
}
