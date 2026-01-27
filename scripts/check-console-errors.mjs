/**
 * Check for critical console errors in the browser
 * Usage: node scripts/check-console-errors.mjs [url]
 */

import http from 'http';
import { WebSocket } from 'ws';

const url = process.argv[2] || 'http://localhost:9000/downloads';

const tabs = await new Promise((resolve) => {
  http.get('http://127.0.0.1:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => resolve(JSON.parse(data)));
  });
});

const ws = new WebSocket(tabs[0].webSocketDebuggerUrl);
const errors = [];

ws.on('open', () => {
  // Navigate to URL
  ws.send(JSON.stringify({ id: 0, method: 'Page.navigate', params: { url } }));
  ws.send(JSON.stringify({ id: 1, method: 'Log.enable' }));
  ws.send(JSON.stringify({ id: 2, method: 'Runtime.enable' }));

  setTimeout(() => {
    // Filter out ignorable errors
    const critical = errors.filter(e => {
      if (e.includes('ERR_CONNECTION_REFUSED')) return false;
      if (e.includes('favicon')) return false;
      return true;
    });

    if (critical.length > 0) {
      console.log('❌ ERRORES CRÍTICOS:', critical.length);
      critical.forEach(e => console.log('  -', e.substring(0, 150)));
      ws.close();
      process.exit(1);
    } else {
      console.log('✅ Sin errores críticos');
      ws.close();
      process.exit(0);
    }
  }, 4000);
});

ws.on('message', (msg) => {
  const r = JSON.parse(msg.toString());
  if (r.method === 'Log.entryAdded' && r.params?.entry?.level === 'error') {
    errors.push(r.params.entry.text);
  }
  if (r.method === 'Runtime.exceptionThrown') {
    errors.push(r.params?.exceptionDetails?.text || 'Exception');
  }
});
