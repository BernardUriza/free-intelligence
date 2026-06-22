/**
 * Identity-scoped store naming — the SSOT for partitioning a local-first store
 * (IndexedDB database, localStorage key) by the authenticated principal.
 *
 * A shell that persists per-user data in the BROWSER (conversation transcripts,
 * an audio queue, a projects list) must NOT share one global store across the
 * accounts that sign in on the same machine — that is a cross-account data leak
 * on shared devices. Deriving the store name from the identity key (the auth
 * principal's `sub`) gives each account its own partition.
 *
 * The result is ALWAYS scoped — there is no unscoped fall-through. A null/empty
 * identity (no auth / legacy bearer single-tenant) maps to an explicit `legacy`
 * partition, NOT the bare base name. This matters in a dual-auth deployment: the
 * pre-fix global store (`base`) holds the leaked, cross-account data, so the
 * runtime must never resolve back to it — a bearer session gets the clean
 * `base--legacy` partition instead. The orphaned `base` store is left untouched
 * (never auto-migrated: better invisible than mis-assigned on a shared device).
 */

const SCOPE_SEPARATOR = '--';
const LEGACY_SCOPE = 'legacy';

export function scopedStoreName(
  base: string,
  identityKey: string | null | undefined,
): string {
  const scope = identityKey && identityKey.trim() ? identityKey : LEGACY_SCOPE;
  return `${base}${SCOPE_SEPARATOR}${scope}`;
}
