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

test("a failed reuse retries the SAME chat on a fresh tab and never opens a new one", async () => {
  const tts = new ArborTTS({ cdpUrl: "http://127.0.0.1:9333", convFile: "/nonexistent/conv" });
  tts.launch = async () => {};
  tts.allowNewChat = false;
  tts.lastConversationUrl = "https://chatgpt.com/c/old";
  const stale = fakePage();
  const targets = [];
  tts._attempt = async (_t, _v, _f, target) => {
    targets.push(target);
    tts.page = stale; throw new Error("slow");
  };
  const errors = [];
  const orig = console.error; console.error = (m) => errors.push(String(m));
  try {
    await assert.rejects(tts._speak("hola", {}), /could not be reused.*Not opening a new chat/s);
  } finally { console.error = orig; }
  assert.deepEqual(targets, ["https://chatgpt.com/c/old", "https://chatgpt.com/c/old"]);
  assert.equal(stale.closed, true);
  assert.equal(tts.lastConversationUrl, "https://chatgpt.com/c/old"); // the saved chat is kept
});

test("a reuse that succeeds on the retry stays in the same chat", async () => {
  const tts = new ArborTTS({ cdpUrl: "http://127.0.0.1:9333", convFile: "/nonexistent/conv" });
  tts.launch = async () => {};
  tts.allowNewChat = false;
  tts.lastConversationUrl = "https://chatgpt.com/c/old";
  const targets = [];
  tts._attempt = async (_t, _v, _f, target) => {
    targets.push(target);
    if (targets.length === 1) { tts.page = fakePage(); throw new Error("slow"); }
    return { ok: true };
  };
  const orig = console.error; console.error = () => {};
  let r; try { r = await tts._speak("hola", {}); } finally { console.error = orig; }
  assert.deepEqual(r, { ok: true });
  assert.deepEqual(targets, ["https://chatgpt.com/c/old", "https://chatgpt.com/c/old"]);
});

test("a gone chat is not retried, and a new chat needs ARBOR_ALLOW_NEW_CHAT", async () => {
  const tts = new ArborTTS({ cdpUrl: "http://127.0.0.1:9333", convFile: "/nonexistent/conv" });
  tts.launch = async () => {};
  tts.allowNewChat = true;
  tts.lastConversationUrl = "https://chatgpt.com/c/old";
  const targets = [];
  tts._attempt = async (_t, _v, _f, target) => {
    targets.push(target);
    if (target.endsWith("/old")) { tts.page = fakePage(); throw new Error("conversation old is not accessible"); }
    return { ok: true };
  };
  const orig = console.error; console.error = () => {};
  try { await tts._speak("hola", {}); } finally { console.error = orig; }
  assert.equal(targets.length, 2);                  // one reuse attempt, then the explicit new chat
  assert.equal(targets[0], "https://chatgpt.com/c/old");
  assert.notEqual(targets[1], "https://chatgpt.com/c/old");
});
