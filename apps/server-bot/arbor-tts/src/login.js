import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

// One-time interactive login. Opens a VISIBLE browser, you log into ChatGPT by
// hand (Google OAuth, captcha, whatever), and the resulting cookies/localStorage
// are saved to AUTH_STATE for the headless service to reuse.
const AUTH_STATE = process.env.AUTH_STATE || "./auth/state.json";
const LOGIN_TIMEOUT_MS = 5 * 60 * 1000;

async function main() {
  fs.mkdirSync(path.dirname(AUTH_STATE), { recursive: true });
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("→ Opening chatgpt.com. Log in with your account in the window.");
  await page.goto("https://chatgpt.com/");
  console.log("→ Waiting for a logged-in session (up to 5 min)...");

  const deadline = Date.now() + LOGIN_TIMEOUT_MS;
  let ok = false;
  while (Date.now() < deadline) {
    const sess = await page
      .evaluate(async () => {
        try {
          return await (await fetch("/api/auth/session")).json();
        } catch {
          return null;
        }
      })
      .catch(() => null);
    if (sess && sess.accessToken) {
      ok = true;
      break;
    }
    await page.waitForTimeout(2000);
  }

  if (!ok) {
    console.error("✗ Timed out without a logged-in session.");
    await browser.close();
    process.exit(1);
  }

  await context.storageState({ path: AUTH_STATE });
  console.log(`✓ Auth saved to ${AUTH_STATE}`);
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
