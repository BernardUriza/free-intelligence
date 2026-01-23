import WebSocket from 'ws';
import fs from 'fs';

const tabsRes = await fetch('http://127.0.0.1:9222/json/list');
const tabs = await tabsRes.json();
const pageTab = tabs.find(t => t.type === 'page');

const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
await new Promise(resolve => ws.on('open', resolve));

let msgId = 1;
const send = (method, params = {}) => new Promise(r => {
  const id = msgId++;
  ws.on('message', function h(d) {
    const m = JSON.parse(d);
    if (m.id === id) { ws.off('message', h); r(m); }
  });
  ws.send(JSON.stringify({ id, method, params }));
});

// Set a smaller viewport to force scroll
await send('Emulation.setDeviceMetricsOverride', {
  width: 1280,
  height: 600,
  deviceScaleFactor: 1,
  mobile: false
});

// Navigate and wait
await send('Page.navigate', { url: 'https://app.aurity.io/downloads/' });
await new Promise(r => setTimeout(r, 5000));

// Check scroll state
const scrollCheck = await send('Runtime.evaluate', {
  expression: `
    const scrollContainer = document.querySelector('div.overflow-y-auto') || document.body;
    ({
      element: scrollContainer.className,
      scrollTop: scrollContainer.scrollTop,
      scrollHeight: scrollContainer.scrollHeight,
      clientHeight: scrollContainer.clientHeight,
      canScroll: scrollContainer.scrollHeight > scrollContainer.clientHeight
    });
  `,
  returnByValue: true
});
console.log('Scroll state:', scrollCheck.result?.result?.value);

// Try to scroll
await send('Runtime.evaluate', {
  expression: `
    const scrollContainer = document.querySelector('div.overflow-y-auto') || document.body;
    scrollContainer.scrollTop = 300;
  `
});
await new Promise(r => setTimeout(r, 500));

// Check scroll position after
const afterScroll = await send('Runtime.evaluate', {
  expression: `
    const scrollContainer = document.querySelector('div.overflow-y-auto') || document.body;
    ({ scrollTop: scrollContainer.scrollTop });
  `,
  returnByValue: true
});
console.log('After scroll:', afterScroll.result?.result?.value);

// Take screenshot
const result = await send('Page.captureScreenshot', { format: 'png' });
if (result.result && result.result.data) {
  const imgBuffer = Buffer.from(result.result.data, 'base64');
  fs.writeFileSync('C:/Users/buo45/Downloads/downloads-small-viewport.png', imgBuffer);
  console.log('Screenshot saved');
}

// Reset viewport
await send('Emulation.clearDeviceMetricsOverride', {});

ws.close();
