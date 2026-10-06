import { test } from "node:test";
import assert from "node:assert/strict";
import { latestAssistant } from "../src/synthesize.js";

const node = (id, parent, role, text, status = "finished_successfully") => ({
  id, parent, message: { id, author: { role }, status, content: { parts: [text] } },
});

test("returns the newest assistant reply on the active branch", () => {
  const conv = {
    current_node: "a2",
    mapping: {
      u1: node("u1", null, "user", "hola"),
      a1: node("a1", "u1", "assistant", "hola 🎉"),
      u2: node("u2", "a1", "user", "otra"),
      a2: node("a2", "u2", "assistant", "otra 🎉"),
    },
  };
  assert.deepEqual(latestAssistant(conv), { id: "a2", done: true, text: "otra 🎉" });
});

test("a still-streaming reply is reported as not done", () => {
  const conv = { current_node: "a1", mapping: {
    u1: node("u1", null, "user", "x"), a1: node("a1", "u1", "assistant", "x", "in_progress") } };
  assert.equal(latestAssistant(conv).done, false);
});

test("skips empty assistant/tool nodes and returns null before any reply", () => {
  const conv = { current_node: "t1", mapping: {
    u1: node("u1", null, "user", "x"), t1: node("t1", "u1", "assistant", "") } };
  assert.equal(latestAssistant(conv), null);
  assert.equal(latestAssistant(null), null);
});
