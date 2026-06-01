import fs from "node:fs";
import path from "node:path";
import { ArborTTS } from "./synthesize.js";
import { resolveVoice } from "./voices.js";
import { outputName } from "./naming.js";

// Usage: node src/cli.js "text to speak" [voice] [out.(mp3|aac|opus)]
// `voice` and `out` are optional and order-independent. If no output path is
// given, a unique name is auto-generated under output/.
const argv = process.argv.slice(2);
const text = argv.shift();
if (!text) {
  console.error(
    'Usage: node src/cli.js "text to speak" [voice] [out.(mp3|aac|opus)]',
  );
  process.exit(1);
}

const AUDIO_EXT = /\.(mp3|aac|opus|ogg|m4a)$/i;
let voiceArg, outPath;
for (const a of argv) {
  if (AUDIO_EXT.test(a) || a.includes("/")) outPath = a;
  else voiceArg = a;
}

async function main() {
  const v = resolveVoice(voiceArg || process.env.ARBOR_VOICE || "arbor");
  const format =
    (outPath && outPath.split(".").pop().toLowerCase()) ||
    process.env.ARBOR_FORMAT ||
    "mp3";
  const finalPath =
    outPath || outputName(text, { voice: v.name.toLowerCase(), format });
  fs.mkdirSync(path.dirname(finalPath), { recursive: true });

  const tts = new ArborTTS();
  try {
    const r = await tts.speak(text, { voice: v.id, format });
    fs.writeFileSync(finalPath, r.buffer);
    console.log(
      `✓ ${r.bytes} bytes (${r.contentType}, voice=${v.name}/${r.voice}) → ${finalPath}`,
    );
  } finally {
    await tts.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
