import { chromium } from "playwright";
import fs from "node:fs";

const STEP_TIMEOUT = 60_000;

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
    // fresh chat every time: less history clutter, fewer conversation-creation
    // calls (lower anti-bot footprint). Falls back to a new chat if the saved
    // conversation is gone.
    this.lastConversationUrl = null;
  }

  async launch() {
    if (this.context) return;
    if (this.cdpUrl) {
      this.browser = await chromium.connectOverCDP(this.cdpUrl);
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
    const run = () => this._speak(text, opts);
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
        this.lastConversationUrl = null;
      }
    }
    return await this._attempt(text, voice, format, this.gptUrl);
  }

  /** One synthesis attempt against `target` (a conversation URL or GPT base). */
  async _attempt(text, voice, format, target) {
    const reuse = target !== this.gptUrl;
    const page = await this.context.newPage();
    try {
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

      // Remember this conversation so the next request reuses it.
      this.lastConversationUrl = page.url();

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
    } finally {
      await page.close().catch(() => {});
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
    this.browser = this.context = null;
    this._cdp = false;
  }
}
