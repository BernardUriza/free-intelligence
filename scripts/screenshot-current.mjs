// Screenshot current state WITHOUT navigating
import fs from 'fs';
import WebSocket from 'ws';

const CDP_URL = 'http://127.0.0.1:9222';
const OUTPUT_PATH = process.argv[2] || '/tmp/screenshot.png';

async function main() {
  const tabsRes = await fetch(`${CDP_URL}/json/list`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.type === 'page' && t.url.includes('localhost:9000'));

  if (!pageTab) {
    console.error('No tab found with localhost:9000');
    process.exit(1);
  }

  console.log(`Tab: ${pageTab.url}`);

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));

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

  // Take screenshot WITHOUT navigating
  console.log('Taking screenshot of current state...');
  const result = await sendCommand('Page.captureScreenshot', { format: 'png' });

  if (result.result && result.result.data) {
    const imgBuffer = Buffer.from(result.result.data, 'base64');
    fs.writeFileSync(OUTPUT_PATH, imgBuffer);
    console.log(`Saved: ${OUTPUT_PATH}`);
  } else {
    console.error('Failed to capture');
  }

  ws.close();
}

main().catch(console.error);
