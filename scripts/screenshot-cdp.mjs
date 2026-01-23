// Screenshot using Chrome DevTools Protocol
import fs from 'fs';
import WebSocket from 'ws';

const CDP_URL = 'http://127.0.0.1:9222';
const TARGET_URL = process.argv[2] || 'https://app.aurity.io/downloads/';
const OUTPUT_PATH = process.argv[3] || 'C:/Users/buo45/Downloads/screenshot.png';
const SCROLL_Y = parseInt(process.argv[4] || '0', 10);

async function main() {
  const tabsRes = await fetch(`${CDP_URL}/json/list`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.type === 'page');

  if (!pageTab) {
    console.error('No page tab found');
    process.exit(1);
  }

  console.log(`Found tab: ${pageTab.title}`);

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  console.log('Connected to CDP');

  let msgId = 1;
  const sendCommand = (method, params = {}) => {
    return new Promise((resolve) => {
      const id = msgId++;
      const handler = (data) => {
        const msg = JSON.parse(data);
        if (msg.id === id) {
          ws.off('message', handler);
          resolve(msg);
        }
      };
      ws.on('message', handler);
      ws.send(JSON.stringify({ id, method, params }));
    });
  };

  // Force navigate (hard refresh)
  console.log(`Navigating to: ${TARGET_URL}`);
  await sendCommand('Page.navigate', { url: TARGET_URL });
  await new Promise(r => setTimeout(r, 5000));

  // Scroll using Runtime.evaluate
  if (SCROLL_Y > 0) {
    console.log(`Scrolling to Y: ${SCROLL_Y}`);
    const scrollResult = await sendCommand('Runtime.evaluate', {
      expression: `window.scrollTo(0, ${SCROLL_Y}); ({scrollY: window.scrollY, scrollHeight: document.body.scrollHeight})`,
      returnByValue: true
    });
    console.log('Scroll result:', scrollResult.result?.result?.value);
    await new Promise(r => setTimeout(r, 500));
  }

  // Take screenshot
  console.log('Taking screenshot...');
  const result = await sendCommand('Page.captureScreenshot', { format: 'png' });

  if (result.result && result.result.data) {
    const imgBuffer = Buffer.from(result.result.data, 'base64');
    fs.writeFileSync(OUTPUT_PATH, imgBuffer);
    console.log(`Screenshot saved to: ${OUTPUT_PATH}`);
  } else {
    console.error('Failed to capture screenshot:', result);
  }

  ws.close();
}

main().catch(console.error);
