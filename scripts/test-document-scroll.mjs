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

// Set smaller viewport
await send('Emulation.setDeviceMetricsOverride', {
  width: 1280,
  height: 600,
  deviceScaleFactor: 1,
  mobile: false
});

// Navigate
await send('Page.navigate', { url: 'https://app.aurity.io/downloads/' });
await new Promise(r => setTimeout(r, 5000));

// Check document scroll state BEFORE scroll
const beforeScroll = await send('Runtime.evaluate', {
  expression: `({
    scrollY: window.scrollY,
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
    bodyScrollHeight: document.body.scrollHeight,
    bodyClientHeight: document.body.clientHeight,
    canScroll: document.documentElement.scrollHeight > document.documentElement.clientHeight
  })`,
  returnByValue: true
});
console.log('Before scroll:', beforeScroll.result?.result?.value);

// Try to scroll document
await send('Runtime.evaluate', {
  expression: `window.scrollTo(0, 300)`
});
await new Promise(r => setTimeout(r, 500));

// Check scroll state AFTER scroll
const afterScroll = await send('Runtime.evaluate', {
  expression: `({ scrollY: window.scrollY })`,
  returnByValue: true
});
console.log('After scroll:', afterScroll.result?.result?.value);

// Take screenshot
const result = await send('Page.captureScreenshot', { format: 'png' });
if (result.result && result.result.data) {
  const imgBuffer = Buffer.from(result.result.data, 'base64');
  fs.writeFileSync('C:/Users/buo45/Downloads/downloads-doc-scroll.png', imgBuffer);
  console.log('Screenshot saved');
}

// Reset viewport
await send('Emulation.clearDeviceMetricsOverride', {});
ws.close();
