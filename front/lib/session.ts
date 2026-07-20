/**
 * The session cookie — a signed token, not a stored one.
 *
 * There is no session table, because there is no session to store: the cookie
 * carries its own expiry and an HMAC over it, so the server can tell a token it
 * minted from one someone typed. Statelessness is the point — the container stores
 * nothing (the daemon's law, and this repo keeps it too), and a restart must not
 * log anyone out.
 *
 * The signature is over the expiry, keyed with the console password. Change the
 * password and every outstanding cookie dies with it, which is exactly what
 * changing a password should mean.
 *
 * Web Crypto only: this must run in the Edge runtime where the middleware lives,
 * and `node:crypto` does not.
 */

const enc = new TextEncoder();

export const COOKIE = "aire_session";
const TTL_MS = 7 * 24 * 60 * 60 * 1000;

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function toBase64Url(bytes: ArrayBuffer): string {
  const binary = String.fromCharCode(...new Uint8Array(bytes));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(text: string): Uint8Array {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

/** A token good for a week: `<expiry>.<hmac(expiry)>`. */
export async function mint(secret: string): Promise<string> {
  const expiry = String(Date.now() + TTL_MS);
  const signature = await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(expiry));
  return `${expiry}.${toBase64Url(signature)}`;
}

/** True only if WE signed it and it has not expired. `crypto.subtle.verify` is
 *  constant-time, so a forged signature leaks nothing by how long it takes to
 *  reject. */
export async function valid(token: string | undefined, secret: string): Promise<boolean> {
  if (!token) return false;
  const cut = token.lastIndexOf(".");
  if (cut < 1) return false;

  const expiry = token.slice(0, cut);
  const signature = token.slice(cut + 1);
  if (!/^\d+$/.test(expiry) || Number(expiry) < Date.now()) return false;

  try {
    return await crypto.subtle.verify(
      "HMAC",
      await hmacKey(secret),
      fromBase64Url(signature) as unknown as ArrayBuffer,
      enc.encode(expiry),
    );
  } catch {
    return false;
  }
}

/** Compare the typed password in constant time. A byte-by-byte early return leaks
 *  it one character at a time to anyone patient enough to measure the reply. */
export function sameSecret(typed: string, expected: string): boolean {
  const a = enc.encode(typed);
  const b = enc.encode(expected);
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a[i] ?? 0) ^ (b[i] ?? 0);
  }
  return diff === 0;
}
