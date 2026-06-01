import crypto from "node:crypto";

// Filesystem-safe slug from arbitrary text: strip accents, lowercase,
// non-alphanumerics -> hyphens, capped length.
export function slugify(text, max = 40) {
  const s = String(text)
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // drop diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, max)
    .replace(/-+$/g, "");
  return s || "audio";
}

// Deterministic, collision-resistant output name:
//   <timestamp>_<voice>_<slug>_<hash>.<ext>
//   2026-06-01T16-22-03_arbor_la-historia-de-alemania_a1b2c3.mp3
//
// timestamp -> chronological, never overwrites
// voice     -> distinguishes arbor/cove/ember/...
// slug      -> human-recognizable
// hash      -> short sha256 of the text (same text => same hash)
export function outputName(text, opts = {}) {
  const { voice = "arbor", format = "mp3", dir = "output" } = opts;
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const hash = crypto
    .createHash("sha256")
    .update(String(text))
    .digest("hex")
    .slice(0, 6);
  const name = `${ts}_${voice}_${slugify(text)}_${hash}.${format}`;
  return dir ? `${dir}/${name}` : name;
}
