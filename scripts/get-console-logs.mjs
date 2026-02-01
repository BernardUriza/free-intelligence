// Get detailed console logs using CDP
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

  // Enable Runtime and Log domains
  await sendCommand('Runtime.enable');
  await sendCommand('Log.enable');

  console.log('Listening for console messages...\n');

  // Listen for console messages
  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    if (msg.method === 'Runtime.consoleAPICalled') {
      const { type, args, stackTrace } = msg.params;
      console.log(`[${type.toUpperCase()}]`);
      args.forEach(arg => {
        if (arg.type === 'string') {
          console.log('  ', arg.value);
        } else if (arg.preview) {
          console.log('  ', arg.preview.description);
        }
      });
      if (stackTrace) {
        console.log('  Stack:', stackTrace.callFrames[0]?.url);
      }
      console.log();
    }

    if (msg.method === 'Runtime.exceptionThrown') {
      const { exceptionDetails } = msg.params;
      console.log('[EXCEPTION]');
      console.log('  ', exceptionDetails.text);
      if (exceptionDetails.exception) {
        console.log('  ', exceptionDetails.exception.description);
      }
      if (exceptionDetails.stackTrace) {
        exceptionDetails.stackTrace.callFrames.forEach(frame => {
          console.log(`    at ${frame.functionName || 'anonymous'} (${frame.url}:${frame.lineNumber})`);
        });
      }
      console.log();
    }
  });

  // Reload page to capture all logs from start
  await sendCommand('Page.reload', { ignoreCache: true });

  // Wait to collect logs
  await new Promise(r => setTimeout(r, 5000));

  ws.close();
}

main().catch(console.error);
