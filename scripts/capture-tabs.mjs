// Capture screenshots of Fi-Monitor tabs using CDP
import fs from 'fs';
import WebSocket from 'ws';

const CDP_URL = 'http://127.0.0.1:9222';
const APP_URL = 'http://localhost:1420/';

async function main() {
  // Find the Fi-Monitor tab
  const tabsRes = await fetch(`${CDP_URL}/json/list`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.url === APP_URL);

  if (!pageTab) {
    console.error('Fi-Monitor tab not found');
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

  // Enable Page domain
  await sendCommand('Page.enable');

  // Tabs to capture: Config (index 2) and Benchmarks (index 4)
  const tabsToCapture = [
    { index: 2, name: 'config', description: 'Config tab with EnvVarEditor' },
    { index: 4, name: 'benchmarks', description: 'Benchmarks tab with historical charts' }
  ];

  for (const tab of tabsToCapture) {
    console.log(`\nCapturing ${tab.description}...`);

    // Click the sidebar tab
    await sendCommand('Runtime.evaluate', {
      expression: `document.querySelectorAll(".sidebar-tab")[${tab.index}].click()`
    });

    // Wait for content to render
    await new Promise(r => setTimeout(r, 2000));

    // Scroll down to show more content
    await sendCommand('Runtime.evaluate', {
      expression: 'window.scrollTo(0, document.body.scrollHeight / 2)'
    });
    await new Promise(r => setTimeout(r, 500));

    // Take screenshot
    const result = await sendCommand('Page.captureScreenshot', { format: 'png' });

    if (result.result && result.result.data) {
      const outputPath = `/tmp/fi-monitor-${tab.name}-tab.png`;
      const imgBuffer = Buffer.from(result.result.data, 'base64');
      fs.writeFileSync(outputPath, imgBuffer);
      console.log(`✅ Screenshot saved: ${outputPath}`);
    } else {
      console.error(`❌ Failed to capture ${tab.name} tab:`, result);
    }
  }

  ws.close();
  console.log('\n✅ All screenshots captured!');
}

main().catch(console.error);
