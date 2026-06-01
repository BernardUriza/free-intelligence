import express from "express";
import fs from "node:fs";
import path from "node:path";
import { ArborTTS } from "./synthesize.js";
import { resolveVoice } from "./voices.js";
import { outputName } from "./naming.js";

const PORT = Number(process.env.PORT || 8799);
const SERVICE_TOKEN = process.env.SERVICE_TOKEN || "";

const tts = new ArborTTS();
const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => res.json({ status: "ok" }));

// POST /tts { text, voice?, format? } -> audio bytes (Content-Type per format)
app.post("/tts", async (req, res) => {
  if (SERVICE_TOKEN) {
    if ((req.get("authorization") || "") !== `Bearer ${SERVICE_TOKEN}`) {
      return res.status(401).json({ error: "unauthorized" });
    }
  }
  const { text, voice, format, save } = req.body || {};
  if (!text || typeof text !== "string") {
    return res.status(400).json({ error: "missing 'text' (string)" });
  }
  try {
    const v = resolveVoice(voice || process.env.ARBOR_VOICE || "arbor");
    const result = await tts.speak(text, { voice: v.id, format });
    res.set("Content-Type", result.contentType || "application/octet-stream");
    res.set("X-Voice-Id", result.voice);
    res.set("X-Voice-Name", v.name);
    res.set("Content-Length", String(result.bytes));
    // Optional: also persist to disk with the deterministic naming scheme.
    if (save) {
      const fmt = format || process.env.ARBOR_FORMAT || "mp3";
      const p = outputName(text, { voice: v.name.toLowerCase(), format: fmt });
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, result.buffer);
      res.set("X-Saved-Path", p);
    }
    res.send(result.buffer);
  } catch (e) {
    res.status(500).json({ error: String((e && e.message) || e) });
  }
});

const server = app.listen(PORT, () =>
  console.log(`arbor-tts listening on http://localhost:${PORT}`),
);

async function shutdown() {
  await tts.close();
  server.close(() => process.exit(0));
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
