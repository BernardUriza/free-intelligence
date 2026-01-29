// Capture Services tab with Model Manager expanded
import fs from 'fs';
import WebSocket from 'ws';

const CDP_URL = 'http://127.0.0.1:9222';
const APP_URL = 'http://localhost:1420/';

async function main() {
  const tabsRes = await fetch(`${CDP_URL}/json/list`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.url === APP_URL);

  if (!pageTab) {
    console.error('Fi-Monitor tab not found');
    process.exit(1);
  }

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

  await sendCommand('Page.enable');

  console.log('Navigating to Services tab...');
  await sendCommand('Runtime.evaluate', {
    expression: `document.querySelectorAll(".sidebar-tab")[0].click()`
  });
  await new Promise(r => setTimeout(r, 1500));

  // Find and list all buttons
  console.log('Finding buttons...');
  const buttonsResult = await sendCommand('Runtime.evaluate', {
    expression: `
      Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim())
    `,
    returnByValue: true
  });
  console.log('Available buttons:', buttonsResult.result.value);

  // Click "Show Models" button (more specific)
  console.log('Clicking Show Models button...');
  const clickResult = await sendCommand('Runtime.evaluate', {
    expression: `
      const btn = Array.from(document.querySelectorAll('button')).find(b =>
        b.textContent.includes('Show Models')
      );
      if (btn) {
        btn.click();
        'clicked';
      } else {
        'button not found';
      }
    `,
    returnByValue: true
  });
  console.log('Click result:', clickResult.result.value);

  await new Promise(r => setTimeout(r, 2000));

  // Scroll to show Model Manager
  await sendCommand('Runtime.evaluate', {
    expression: 'window.scrollTo(0, 400)'
  });
  await new Promise(r => setTimeout(r, 500));

  // Take screenshot
  const result = await sendCommand('Page.captureScreenshot', { format: 'png' });

  if (result.result && result.result.data) {
    const outputPath = '/tmp/fi-monitor-services-models.png';
    const imgBuffer = Buffer.from(result.result.data, 'base64');
    fs.writeFileSync(outputPath, imgBuffer);
    console.log(`✅ Screenshot saved: ${outputPath}`);
  }

  ws.close();
}

main().catch(console.error);
