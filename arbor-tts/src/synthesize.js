import { chromium } from "playwright";
import fs from "node:fs";

const STEP_TIMEOUT = 60_000;
// Hard ceiling for a whole speak() so a hung Playwright op can never wedge the
// serialized queue (the recurring "voice goes silent until hard-restart" bug).
const SPEAK_TIMEOUT = 150_000;

/**
 * ArborTTS — a headless black box that turns text into ChatGPT "Arbor" (fathom)
 * voice audio. It replicates exactly what we did by hand:
 *   1. open an echo GPT, send the text, wait for the assistant echo,
 *   2. read the assistant message_id + conversation_id,
 *   3. GET /backend-api/synthesize?...&voice=fathom&format=mp3 with the session
 *      Bearer token, and return the audio buffer.
 *
 * One browser/context is reused across calls; requests are serialized because a
 * single ChatGPT web session drives one conversation at a time.
 */
export class ArborTTS {
  constructor(opts = {}) {
    this.gptUrl =
      opts.gptUrl || process.env.CHATGPT_GPT_URL || "https://chatgpt.com/";
    this.authState = opts.authState || process.env.AUTH_STATE || "./auth/state.json";
    this.headless = opts.headless ?? process.env.HEADLESS !== "0";
    // CDP mode: attach to an already-running, already-logged-in Chrome
    // (e.g. a remote-debugging profile on :9222) instead of launching one.
    // Sidesteps the login dance and Cloudflare headless challenges entirely.
    this.cdpUrl = opts.cdpUrl || process.env.CDP_URL || "";
    this.browser = null;
    this.context = null;
    this._cdp = false;
    this._queue = Promise.resolve();
    // Reuse the same ChatGPT conversation across requests instead of starting a
    // fresh chat every time. PERSISTED to disk so it survives service restarts /
    // reboots → never creates a new chat unless the saved one is gone.
    this.convFile = opts.convFile || process.env.CONV_STATE_FILE || ".last_conversation";
    this.lastConversationUrl = this._loadConv();
    // One reused page (tab) across requests. Opening a fresh tab per request
    // raised Chrome to the foreground and stole focus; reusing one tab avoids it.
    this.page = null;
  }

  _loadConv() {
    try {
      const u = fs.readFileSync(this.convFile, "utf8").trim();
      return u || null;
    } catch {
      return null;
    }
  }

  _setConv(url) {
    this.lastConversationUrl = url || null;
    try {
      if (url) fs.writeFileSync(this.convFile, url);
    } catch {
      /* best-effort persistence */
    }
  }

  /** Return the single reused page, creating it once if missing/closed. */
  async _getPage() {
    if (this.page && !this.page.isClosed()) return this.page;
    this.page = await this.context.newPage();
    return this.page;
  }

  async launch() {
    // Reuse a LIVE connection only. If the browser dropped (Chrome restarted
    // by KeepAlive, or the service started before Chrome was up after a reboot),
    // drop the stale handles and reconnect — otherwise every request would hang
    // on a dead CDP socket.
    if (this.context && this.browser && this.browser.isConnected()) return;
    this.context = null;
    this.page = null;
    if (this.cdpUrl) {
      this.browser = await chromium.connectOverCDP(this.cdpUrl, { timeout: 15000 });
      const contexts = this.browser.contexts();
      this.context = contexts[0] || (await this.browser.newContext());
      this._cdp = true;
      return;
    }
    if (!fs.existsSync(this.authState)) {
      throw new Error(
        `No auth state at ${this.authState}. Run \`npm run login\` first.`,
      );
    }
    this.browser = await chromium.launch({ headless: this.headless });
    this.context = await this.browser.newContext({
      storageState: this.authState,
      viewport: { width: 1280, height: 900 },
      userAgent:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    });
  }

  /** Public entry point. Serialized via an internal promise queue. */
  speak(text, opts = {}) {
    const run = async () => {
      try {
        return await Promise.race([
          this._speak(text, opts),
          new Promise((_, reject) =>
            setTimeout(
              () => reject(new Error("speak timed out")),
              SPEAK_TIMEOUT,
            ),
          ),
        ]);
      } catch (e) {
        // A hung/failed request must NOT wedge the queue. Drop the cached page
        // so the next request opens a fresh one; launch() reconnects if the
        // browser itself died. The queue then moves on instead of hanging.
        this.page = null;
        throw e;
      }
    };
    // chain on both fulfil and reject so one failure doesn't wedge the queue
    this._queue = this._queue.then(run, run);
    return this._queue;
  }

  async _speak(text, opts = {}) {
    if (!text || !String(text).trim()) throw new Error("empty text");
    await this.launch();
    const voice = opts.voice || process.env.ARBOR_VOICE || "fathom";
    const format = opts.format || process.env.ARBOR_FORMAT || "mp3";

    // Reuse the last conversation; on ANY failure (gone, slow, id-resolution,
    // Playwright error) reset it and retry ONCE in a fresh chat — "new chat
    // only as a fallback".
    if (this.lastConversationUrl) {
      try {
        return await this._attempt(text, voice, format, this.lastConversationUrl);
      } catch {
        // Reuse failed: drop the saved conversation AND the page (it may be
        // crashed/stale after a Chrome restart), then retry in a fresh chat.
        this.lastConversationUrl = null;
        this.page = null;
      }
    }
    try {
      return await this._attempt(text, voice, format, this.gptUrl);
    } catch (e) {
      // Leave no crashed/stale page cached for the next request.
      this.page = null;
      throw e;
    }
  }

  /** One synthesis attempt against `target` (a conversation URL or GPT base). */
  async _attempt(text, voice, format, target) {
    const reuse = target !== this.gptUrl;
    const page = await this._getPage();
    {
      const composer = page.locator("#prompt-textarea");
      await page.goto(target, {
        waitUntil: "domcontentloaded",
        timeout: STEP_TIMEOUT,
      });
      // Fast-fail when reusing so we fall back quickly; patient for a new chat.
      await composer.waitFor({
        state: "visible",
        timeout: reuse ? 12_000 : STEP_TIMEOUT,
      });

      // Remember the current last assistant id so we can tell the NEW reply
      // apart from prior ones when reusing a conversation.
      const prevAssistantId = await page
        .locator('[data-message-author-role="assistant"]')
        .last()
        .getAttribute("data-message-id")
        .catch(() => null);

      await composer.click();
      await composer.fill(String(text));
      await page.keyboard.press("Enter");

      const assistant = page
        .locator('[data-message-author-role="assistant"]')
        .last();
      await assistant.waitFor({ state: "attached", timeout: STEP_TIMEOUT });
      await this._waitStreamDone(page, assistant);

      // Resolve the REAL ids. Right after sending, the DOM carries a temporary
      // placeholder id (e.g. "request-placeholder-..." / "request-WEB:...") and
      // the URL has not yet flipped to /c/<uuid>. Poll until both are real:
      // a UUID-shaped message id and a conversation id in the URL.
      const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      let messageId = null;
      let conversationId;
      const idDeadline = Date.now() + 30_000;
      while (Date.now() < idDeadline) {
        messageId = await page
          .locator('[data-message-author-role="assistant"]')
          .last()
          .getAttribute("data-message-id")
          .catch(() => null);
        conversationId = (page.url().match(/\/c\/([0-9a-f-]{36})/) || [])[1];
        // Must be a real UUID, have a conversation id, AND be a NEW message
        // (different from the last one when reusing a conversation).
        if (
          messageId &&
          UUID_RE.test(messageId) &&
          conversationId &&
          messageId !== prevAssistantId
        )
          break;
        await page.waitForTimeout(400);
      }
      if (
        !messageId ||
        !UUID_RE.test(messageId) ||
        !conversationId ||
        messageId === prevAssistantId
      ) {
        throw new Error(
          `could not resolve ids (message_id=${messageId} conversation_id=${conversationId})`,
        );
      }

      // Remember this conversation so the next request reuses it (persisted to
      // disk so it also survives a service restart / reboot).
      this._setConv(page.url());

      const audio = await page.evaluate(
        async ({ messageId, conversationId, voice, format }) => {
          const sess = await (await fetch("/api/auth/session")).json();
          const token = sess && sess.accessToken;
          if (!token) throw new Error("no accessToken (login expired?)");
          const url =
            `/backend-api/synthesize?message_id=${messageId}` +
            `&conversation_id=${conversationId}&voice=${voice}&format=${format}`;
          const r = await fetch(url, {
            headers: { authorization: "Bearer " + token, accept: "*/*" },
          });
          if (!r.ok) {
            const body = await r.text().catch(() => "");
            throw new Error(`synthesize ${r.status}: ${body.slice(0, 200)}`);
          }
          const bytes = new Uint8Array(await r.arrayBuffer());
          let bin = "";
          const CHUNK = 0x8000;
          for (let i = 0; i < bytes.length; i += CHUNK) {
            bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
          }
          return {
            b64: btoa(bin),
            type: r.headers.get("content-type"),
            bytes: bytes.length,
          };
        },
        { messageId, conversationId, voice, format },
      );

      return {
        buffer: Buffer.from(audio.b64, "base64"),
        contentType: audio.type,
        bytes: audio.bytes,
        voice,
        format,
        messageId,
        conversationId,
      };
    }
  }

  /** Wait until the assistant stopped streaming and its text is stable. */
  async _waitStreamDone(page, assistant) {
    const deadline = Date.now() + STEP_TIMEOUT;
    let last = "";
    let stableSince = Date.now();
    const stopBtn =
      'button[data-testid="stop-button"], button[aria-label="Stop streaming"], button[aria-label="Stop"]';
    while (Date.now() < deadline) {
      const streaming = await page.locator(stopBtn).count().catch(() => 0);
      const txt = (await assistant.innerText().catch(() => "")) || "";
      if (txt !== last) {
        last = txt;
        stableSince = Date.now();
      }
      if (!streaming && txt.length > 0 && Date.now() - stableSince > 1500) return;
      await page.waitForTimeout(300);
    }
    // best-effort: fall through and let synthesize fail loudly if incomplete
  }

  async close() {
    // In CDP mode we are a guest in the user's browser: never close their
    // context/tabs — just drop the CDP connection.
    if (!this._cdp && this.context) await this.context.close().catch(() => {});
    if (this.browser) await this.browser.close().catch(() => {});
    this.browser = this.context = this.page = null;
    this._cdp = false;
  }
}
