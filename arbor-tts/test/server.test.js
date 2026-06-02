import assert from "node:assert/strict";
import http from "node:http";
import test from "node:test";
import { createApp } from "../src/server.js";

function fakeTts() {
  return {
    async speak(_text, opts) {
      const buffer = Buffer.from("mp3");
      return {
        buffer,
        contentType: "audio/mpeg",
        bytes: buffer.length,
        voice: opts.voice,
        format: opts.format,
      };
    },
    async close() {},
  };
}

async function listen(handler) {
  const server = http.createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    server,
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test("POST /tts requires service token when configured", async () => {
  const app = createApp({ tts: fakeTts(), serviceToken: "secret" });
  const srv = await listen(app);
  try {
    const r = await fetch(`${srv.url}/tts`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "hola" }),
    });
    assert.equal(r.status, 401);
  } finally {
    await srv.close();
  }
});

test("POST /tts fails closed when service token is required but missing", async () => {
  const app = createApp({
    tts: fakeTts(),
    serviceToken: "",
    requireServiceToken: true,
  });
  const srv = await listen(app);
  try {
    const r = await fetch(`${srv.url}/tts`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "hola" }),
    });
    assert.equal(r.status, 503);
    assert.match((await r.json()).error, /SERVICE_TOKEN/);
  } finally {
    await srv.close();
  }
});

test("POST /tts enforces per-window request limits", async () => {
  const app = createApp({
    tts: fakeTts(),
    serviceToken: "secret",
    rateMaxRequests: 1,
    rateWindowMs: 60_000,
  });
  const srv = await listen(app);
  try {
    const body = JSON.stringify({ text: "hola" });
    const headers = {
      authorization: "Bearer secret",
      "content-type": "application/json",
    };
    const first = await fetch(`${srv.url}/tts`, { method: "POST", headers, body });
    assert.equal(first.status, 200);
    const second = await fetch(`${srv.url}/tts`, { method: "POST", headers, body });
    assert.equal(second.status, 429);
    assert.equal(second.headers.has("retry-after"), true);
  } finally {
    await srv.close();
  }
});

test("POST /tts returns audio bytes", async () => {
  const app = createApp({ tts: fakeTts(), serviceToken: "secret" });
  const srv = await listen(app);
  try {
    const r = await fetch(`${srv.url}/tts`, {
      method: "POST",
      headers: {
        authorization: "Bearer secret",
        "content-type": "application/json",
      },
      body: JSON.stringify({ text: "hola", voice: "arbor", format: "mp3" }),
    });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get("content-type"), "audio/mpeg");
    assert.equal(r.headers.get("x-voice-name"), "Arbor");
    assert.equal(Buffer.from(await r.arrayBuffer()).toString(), "mp3");
  } finally {
    await srv.close();
  }
});

test("POST /tts can deliver a callback to an allowed host", async () => {
  let callbackBody = null;
  const callback = await listen((req, res) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      callbackBody = JSON.parse(body);
      res.writeHead(204).end();
    });
  });
  const app = createApp({
    tts: fakeTts(),
    serviceToken: "secret",
    callbackAllowlist: ["127.0.0.1"],
  });
  const srv = await listen(app);
  try {
    const r = await fetch(`${srv.url}/tts`, {
      method: "POST",
      headers: {
        authorization: "Bearer secret",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        text: "hola",
        callback_url: callback.url,
        request_id: "r1",
      }),
    });
    assert.equal(r.status, 200);
    assert.equal((await r.json()).status, "delivered");
    assert.equal(callbackBody.request_id, "r1");
    assert.equal(callbackBody.audio_base64, Buffer.from("mp3").toString("base64"));
  } finally {
    await srv.close();
    await callback.close();
  }
});
