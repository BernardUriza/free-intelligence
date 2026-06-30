// src/identity/scopedStore.ts
var SCOPE_SEPARATOR = "--";
var LEGACY_SCOPE = "legacy";
function scopedStoreName(base, identityKey) {
  const scope = identityKey && identityKey.trim() ? identityKey : LEGACY_SCOPE;
  return `${base}${SCOPE_SEPARATOR}${scope}`;
}
export {
  scopedStoreName
};
//# sourceMappingURL=index.js.map