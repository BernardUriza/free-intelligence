/**
 * Clipboard Utilities
 *
 * Copy-to-clipboard functions with toast notifications
 *
 * Card: FI-UI-FEAT-100
 */

/**
 * Copy text to clipboard
 *
 * @param text - Text to copy
 * @param label - Optional label for success message
 * @returns Promise<boolean> - Success status
 */
export async function copyToClipboard(
  text: string,
  label?: string
): Promise<boolean> {
  try {
    // Modern Clipboard API (preferred)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      console.log(`[Clipboard] Copied${label ? ` ${label}` : ''}: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`);
      return true;
    }

    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    if (successful) {
      console.log(`[Clipboard] Copied (fallback)${label ? ` ${label}` : ''}: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`);
      return true;
    }

    console.error('[Clipboard] Copy failed');
    return false;
  } catch (err) {
    console.error('[Clipboard] Error:', err);
    return false;
  }
}

/**
 * Copy session ID to clipboard
 *
 * @param sessionId - Session ID to copy
 * @returns Promise<boolean>
 */
export async function copySessionId(sessionId: string): Promise<boolean> {
  return copyToClipboard(sessionId, 'session ID');
}

/**
 * Copy manifest reference to clipboard
 *
 * @param manifestRef - Manifest reference to copy
 * @returns Promise<boolean>
 */
export async function copyManifestRef(manifestRef: string): Promise<boolean> {
  return copyToClipboard(manifestRef, 'manifest ref');
}

/**
 * Copy owner hash to clipboard
 *
 * @param ownerHash - Owner hash to copy
 * @returns Promise<boolean>
 */
export async function copyOwnerHash(ownerHash: string): Promise<boolean> {
  return copyToClipboard(ownerHash, 'owner hash');
}
