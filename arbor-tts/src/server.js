import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ArborTTS } from "./synthesize.js";
import { resolveVoice } from "./voices.js";
import { outputName } from "./naming.js";

const PORT = Number(process.env.PORT || 8799);
const SERVICE_TOKEN = process.env.SERVICE_TOKEN || "";
const REQUIRE_SERVICE_TOKEN = process.env.REQUIRE_SERVICE_TOKEN !== "0";
const TTS_ENABLED = process.env.TTS_ENABLED !== "0";
const MAX_TEXT_CHARS = Number(process.env.MAX_TEXT_CHARS || 4096);
const RATE_LIMIT_WINDOW_MS = Number(process.env.RATE_LIMIT_WINDOW_MS || 60 * 60 * 1000);
const RATE_LIMIT_MAX_REQUESTS = Number(process.env.RATE_LIMIT_MAX_REQUESTS || 20);
const DAILY_REQUEST_CAP = Number(process.env.DAILY_REQUEST_CAP || 100);
const DAILY_TEXT_CHAR_CAP = Number(process.env.DAILY_TEXT_CHAR_CAP || 100_000);
const CALLBACK_ALLOWLIST = (process.env.CALLBACK_ALLOWLIST || "")
  .split(",")
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

function authOk(req, serviceToken) {
  if (!serviceToken) return true;
  return (req.get("authorization") || "") === `Bearer ${serviceToken}`;
}

function clientKey(req) {
  return req.get("authorization") || req.ip || req.socket.remoteAddress || "unknown";
}

function dayKey(now = new Date()) {
  return now.toISOString().slice(0, 10);
}

function createUsageState() {
  return {
    windows: new Map(),
    daily: new Map(),
  };
}

function enforceUsageLimits(req, text, opts = {}) {
  const state = opts.state;
  const now = opts.now || Date.now();
  const rateWindowMs = opts.rateWindowMs ?? RATE_LIMIT_WINDOW_MS;
  const rateMaxRequests = opts.rateMaxRequests ?? RATE_LIMIT_MAX_REQUESTS;
  const dailyRequestCap = opts.dailyRequestCap ?? DAILY_REQUEST_CAP;
  const dailyTextCharCap = opts.dailyTextCharCap ?? DAILY_TEXT_CHAR_CAP;
  const key = clientKey(req);

  if (rateMaxRequests > 0) {
    const current = state.windows.get(key);
    const windowStart =
      current && now - current.windowStart < rateWindowMs ? current.windowStart : now;
    const count = current && windowStart === current.windowStart ? current.count + 1 : 1;
    if (count > rateMaxRequests) {
      const retryAfterMs = rateWindowMs - (now - windowStart);
      return {
        ok: false,
        status: 429,
        retryAfterSeconds: Math.max(1, Math.ceil(retryAfterMs / 1000)),
        error: `rate limit exceeded; max ${rateMaxRequests} requests per ${rateWindowMs}ms`,
      };
    }
    state.windows.set(key, { windowStart, count });
  }

  const dailyKey = `${dayKey(new Date(now))}:${key}`;
  const daily = state.daily.get(dailyKey) || { requests: 0, chars: 0 };
  const next = {
    requests: daily.requests + 1,
    chars: daily.chars + String(text).length,
  };
  if (dailyRequestCap > 0 && next.requests > dailyRequestCap) {
    return {
      ok: false,
      status: 429,
      retryAfterSeconds: 60 * 60,
      error: `daily request cap exceeded; max ${dailyRequestCap}`,
    };
  }
  if (dailyTextCharCap > 0 && next.chars > dailyTextCharCap) {
    return {
      ok: false,
      status: 429,
      retryAfterSeconds: 60 * 60,
      error: `daily text cap exceeded; max ${dailyTextCharCap} characters`,
    };
  }
  state.daily.set(dailyKey, next);
  return { ok: true };
}

function callbackHostAllowed(callbackUrl, allowlist = CALLBACK_ALLOWLIST) {
  if (!allowlist.length) return false;
  const host = new URL(callbackUrl).hostname.toLowerCase();
  return allowlist.some((allowed) => {
    if (allowed.startsWith("*.")) {
      const suffix = allowed.slice(1);
      return host.endsWith(suffix);
    }
    return host === allowed;
  });
}

function cleanCallbackHeaders(headers) {
  if (!headers || typeof headers !== "object" || Array.isArray(headers)) return {};
  const clean = {};
  for (const [k, v] of Object.entries(headers)) {
    const key = String(k).toLowerCase();
    if (!/^[a-z0-9-]+$/.test(key)) continue;
    if (["host", "content-length", "connection"].includes(key)) continue;
    clean[key] = String(v);
  }
  return clean;
}

async function deliverCallback(callbackUrl, callbackHeaders, payload, allowlist) {
  if (!callbackHostAllowed(callbackUrl, allowlist)) {
    throw new Error(
      "callback host is not allowed; set CALLBACK_ALLOWLIST to enable callbacks",
    );
  }
  const r = await fetch(callbackUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...cleanCallbackHeaders(callbackHeaders),
    },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const body = await r.text().catch(() => "");
    throw new Error(`callback ${r.status}: ${body.slice(0, 200)}`);
  }
  return { status: r.status };
}

export function createApp(opts = {}) {
  const tts = opts.tts || new ArborTTS();
  const serviceToken = opts.serviceToken ?? SERVICE_TOKEN;
  const requireServiceToken = opts.requireServiceToken ?? REQUIRE_SERVICE_TOKEN;
  const ttsEnabled = opts.ttsEnabled ?? TTS_ENABLED;
  const usageState = opts.usageState || createUsageState();
  const callbackAllowlist = opts.callbackAllowlist ?? CALLBACK_ALLOWLIST;
  const app = express();
  app.locals.tts = tts;
  app.locals.usageState = usageState;
  app.use(express.json({ limit: "1mb" }));

  app.get("/health", (_req, res) =>
    res.json({
      status: "ok",
      tts_enabled: ttsEnabled,
      auth_required: requireServiceToken,
      auth_configured: Boolean(serviceToken),
    }),
  );

  // POST /tts { text, voice?, format? } -> audio bytes (Content-Type per format)
  // Optional callback mode:
  //   { text, callback_url, callback_headers? } -> JSON with delivery status.
  app.post("/tts", async (req, res) => {
    if (!ttsEnabled) {
      return res.status(503).json({ error: "tts disabled" });
    }
    if (requireServiceToken && !serviceToken) {
      return res.status(503).json({
        error: "SERVICE_TOKEN is required; set REQUIRE_SERVICE_TOKEN=0 only for local testing",
      });
    }
    if (!authOk(req, serviceToken)) {
      return res.status(401).json({ error: "unauthorized" });
    }
    const {
      text,
      voice,
      format,
      save,
      callback_url: callbackUrlSnake,
      callbackUrl: callbackUrlCamel,
      callback_headers: callbackHeadersSnake,
      callbackHeaders: callbackHeadersCamel,
      request_id: requestIdSnake,
      requestId: requestIdCamel,
    } = req.body || {};
    if (!text || typeof text !== "string") {
      return res.status(400).json({ error: "missing 'text' (string)" });
    }
    if (text.length > MAX_TEXT_CHARS) {
      return res.status(413).json({
        error: `text too long; max ${MAX_TEXT_CHARS} characters`,
      });
    }
    const usage = enforceUsageLimits(req, text, {
      state: usageState,
      rateWindowMs: opts.rateWindowMs,
      rateMaxRequests: opts.rateMaxRequests,
      dailyRequestCap: opts.dailyRequestCap,
      dailyTextCharCap: opts.dailyTextCharCap,
    });
    if (!usage.ok) {
      if (usage.retryAfterSeconds) {
        res.set("Retry-After", String(usage.retryAfterSeconds));
      }
      return res.status(usage.status).json({ error: usage.error });
    }
    const callbackUrl = callbackUrlSnake || callbackUrlCamel || "";
    const callbackHeaders = callbackHeadersSnake || callbackHeadersCamel || {};
    const requestId = requestIdSnake || requestIdCamel || null;
    try {
      const v = resolveVoice(voice || process.env.ARBOR_VOICE || "arbor");
      const fmt = format || process.env.ARBOR_FORMAT || "mp3";
      const result = await tts.speak(text, { voice: v.id, format: fmt });
      let savedPath = null;
      if (save) {
        savedPath = outputName(text, { voice: v.name.toLowerCase(), format: fmt });
        fs.mkdirSync(path.dirname(savedPath), { recursive: true });
        fs.writeFileSync(savedPath, result.buffer);
      }

      if (callbackUrl) {
        const delivery = await deliverCallback(
          callbackUrl,
          callbackHeaders,
          {
            request_id: requestId,
            status: "ok",
            voice_id: result.voice,
            voice_name: v.name,
            format: fmt,
            content_type: result.contentType || "application/octet-stream",
            bytes: result.bytes,
            saved_path: savedPath,
            audio_base64: result.buffer.toString("base64"),
          },
          callbackAllowlist,
        );
        return res.status(200).json({
          status: "delivered",
          callback_status: delivery.status,
          request_id: requestId,
          bytes: result.bytes,
          voice_id: result.voice,
          voice_name: v.name,
        });
      }

      res.set("Content-Type", result.contentType || "application/octet-stream");
      res.set("X-Voice-Id", result.voice);
      res.set("X-Voice-Name", v.name);
      res.set("X-Conversation-Id", result.conversationId || "");
      res.set("Content-Length", String(result.bytes));
      if (savedPath) res.set("X-Saved-Path", savedPath);
      res.send(result.buffer);
    } catch (e) {
      res.status(500).json({ error: String((e && e.message) || e) });
    }
  });

  return app;
}

async function shutdown() {
  await app.locals.tts.close();
  server.close(() => process.exit(0));
}

const isMain = process.argv[1] === fileURLToPath(import.meta.url);
let app;
let server;
if (isMain) {
  app = createApp();
  server = app.listen(PORT, () =>
    console.log(`arbor-tts listening on http://localhost:${PORT}`),
  );
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}
