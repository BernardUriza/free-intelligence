// Mapping discovered live from GET /backend-api/synthesize?... and
// GET /backend-api/settings/voices on 2026-06-01.
//
// The ChatGPT UI shows a DISPLAY name (e.g. "Arbor"), but the synthesize
// endpoint wants the INTERNAL id (e.g. "fathom"). Passing a display name
// like "arbor" to synthesize returns 404 — you must pass "fathom".
//
// key   = display name (lowercased, what you pick in ChatGPT settings)
// id    = internal voice id the synthesize endpoint accepts
// name  = pretty display name
export const VOICES = {
  arbor: { id: "fathom", name: "Arbor" }, // <- the voice this service is built around
  cove: { id: "cove", name: "Cove" },
  breeze: { id: "breeze", name: "Breeze" },
  vale: { id: "vale", name: "Vale" },
  maple: { id: "maple", name: "Maple" },
  ember: { id: "ember", name: "Ember" },
  juniper: { id: "juniper", name: "Juniper" },
  spruce: { id: "orbit", name: "Spruce" },
  sol: { id: "glimmer", name: "Sol" },
};

// Accept either a display name ("arbor") or a raw internal id ("fathom").
export function resolveVoice(input) {
  if (!input) return VOICES.arbor;
  const key = String(input).toLowerCase();
  if (VOICES[key]) return VOICES[key];
  const byId = Object.values(VOICES).find((v) => v.id === key);
  if (byId) return byId;
  // Unknown — pass it through as a raw id and let synthesize decide.
  return { id: key, name: key };
}
