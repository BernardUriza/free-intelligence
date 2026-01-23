import WebSocket from 'ws';

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

// Check overflow and scroll on key elements
const result = await send('Runtime.evaluate', {
  expression: `
    const html = document.documentElement;
    const body = document.body;
    const appContainer = body.querySelector('div.min-h-screen');

    const info = {
      html: {
        overflow: getComputedStyle(html).overflow,
        overflowY: getComputedStyle(html).overflowY,
        height: html.clientHeight,
        scrollHeight: html.scrollHeight
      },
      body: {
        overflow: getComputedStyle(body).overflow,
        overflowY: getComputedStyle(body).overflowY,
        height: body.clientHeight,
        scrollHeight: body.scrollHeight
      },
      appContainer: appContainer ? {
        className: appContainer.className,
        overflow: getComputedStyle(appContainer).overflow,
        overflowY: getComputedStyle(appContainer).overflowY,
        height: appContainer.clientHeight,
        scrollHeight: appContainer.scrollHeight
      } : null
    };
    JSON.stringify(info, null, 2);
  `,
  returnByValue: true
});

console.log('Scroll analysis:');
console.log(result.result?.result?.value);

ws.close();
