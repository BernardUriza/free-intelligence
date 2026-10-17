import { test } from "node:test";
import assert from "node:assert/strict";
import { ArborTTS } from "../src/synthesize.js";

const fakePage = () => {
  const page = { closed: false, isClosed: () => page.closed, close: async () => { page.closed = true; } };
  return page;
};

test("close() in CDP mode closes the tab it opened and nothing else", async () => {
  const tts = new ArborTTS({ cdpUrl: "http://127.0.0.1:9333", convFile: "/nonexistent/conv" });
  const ours = fakePage();
  let contextClosed = false;
  tts._cdp = true;
  tts.context = { close: async () => { contextClosed = true; } };
  tts.browser = { close: async () => {} };
  tts.page = ours;
  await tts.close();
  assert.equal(ours.closed, true);       // no ghost tab left behind
  assert.equal(contextClosed, false);     // the user's context (and tabs) are untouched
});

test("a failed conversation reuse closes the stale tab before opening a new chat", async () => {
  const tts = new ArborTTS({ cdpUrl: "http://127.0.0.1:9333", convFile: "/nonexistent/conv" });
  tts.launch = async () => {};
  tts.lastConversationUrl = "https://chatgpt.com/c/old";
  const stale = fakePage();
  const pagesSeen = [];
  tts._attempt = async (_t, _v, _f, target) => {
    pagesSeen.push(tts.page);
    if (target.endsWith("/old")) { tts.page = stale; throw new Error("gone"); }
    return { ok: true };
  };
  const errors = [];
  const orig = console.error; console.error = (m) => errors.push(String(m));
  try { await tts._speak("hola", {}); } finally { console.error = orig; }
  assert.equal(stale.closed, true);
  assert.match(errors.join("\n"), /reusing https:\/\/chatgpt\.com\/c\/old failed \(gone\)/);
});
