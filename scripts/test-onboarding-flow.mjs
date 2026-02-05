/**
 * Test Onboarding Flow
 *
 * Automated test of the complete onboarding flow using CDP via WebSocket.
 * Uses same pattern as screenshot-cdp.mjs
 */

import fs from 'fs';
import WebSocket from 'ws';

const CDP_URL = 'http://127.0.0.1:9222';
const SCRATCHPAD = '/private/tmp/claude-501/-Users-bernardurizaorozco-Documents-free-intelligence/281763e1-f979-4d23-a92b-3ae7f46079b4/scratchpad';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  console.log('🔍 Conectando a Chrome DevTools...');
  const tabsRes = await fetch(`${CDP_URL}/json/list`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.type === 'page' && t.url.includes('localhost:9000'));

  if (!pageTab) {
    console.error('❌ No se encontró tab con localhost:9000');
    console.log('   Tabs disponibles:', tabs.map(t => t.url));
    process.exit(1);
  }

  console.log(`✅ Tab encontrado: ${pageTab.title}`);

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise(resolve => ws.on('open', resolve));
  console.log('✅ Conectado a CDP WebSocket');

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

  const takeScreenshot = async (name) => {
    const result = await sendCommand('Page.captureScreenshot', { format: 'png' });
    if (result.result && result.result.data) {
      const imgBuffer = Buffer.from(result.result.data, 'base64');
      fs.writeFileSync(`${SCRATCHPAD}/${name}.png`, imgBuffer);
      console.log(`📸 Screenshot: ${name}.png`);
    }
  };

  const evaluate = async (expression) => {
    const result = await sendCommand('Runtime.evaluate', {
      expression,
      returnByValue: true
    });
    return result.result?.result?.value;
  };

  try {
    // Step 1: Navigate to onboarding
    console.log('\n🚀 PASO 1: Navegando a /onboarding/...');
    await sendCommand('Page.navigate', { url: 'http://localhost:9000/onboarding/' });

    // Wait for intro to load - check for the actual message content
    console.log('   Esperando intro de Ollama (hasta 60s)...');
    let introLoaded = false;
    for (let i = 0; i < 60; i++) {
      await sleep(1000);
      const hasIntro = await evaluate(`
        document.body.textContent.includes('Free-Intelligence') &&
        document.body.textContent.includes('llamas')
      `);
      if (hasIntro) {
        console.log(`   ✅ Intro cargado después de ${i+1}s`);
        introLoaded = true;
        break;
      }
      if (i % 10 === 9) console.log(`   ... ${i+1}s esperando...`);
    }
    if (!introLoaded) console.log('   ⚠️ Timeout esperando intro');

    await takeScreenshot('01-intro-loaded');

    // Step 2: Type name using CDP Input (simulates real keyboard)
    console.log('\n✏️ PASO 2: Escribiendo nombre "Dr. Prueba"...');

    // Focus the textarea first
    await evaluate(`document.querySelector('textarea')?.focus()`);
    await sleep(200);

    // Type each character using CDP Input.insertText
    const text = 'Dr. Prueba';
    await sendCommand('Input.insertText', { text });
    console.log('   Texto insertado via CDP');
    const inputFound = true;
    console.log('   Input encontrado:', inputFound);
    await sleep(500);
    await takeScreenshot('02-name-typed');

    // Step 3: Submit using Enter key via CDP Input
    console.log('\n📤 PASO 3: Enviando mensaje (Enter via CDP)...');
    await sendCommand('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13
    });
    await sendCommand('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13
    });
    console.log('   Enter key enviado via CDP');

    // Wait for response (poll until not loading)
    console.log('   Esperando respuesta de Ollama (hasta 30s)...');
    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      const loading = await evaluate(`
        document.body.textContent.includes('Cargando') ||
        !!document.querySelector('[class*="animate-spin"]')
      `);
      if (!loading) {
        console.log(`   ✅ Respuesta recibida después de ${i+1}s`);
        break;
      }
      if (i % 10 === 9) console.log(`   ... ${i+1}s esperando...`);
    }
    await sleep(1000); // Extra wait for render
    await takeScreenshot('03-after-name-sent');

    // Debug: Check what messages are in the DOM
    const messagesDebug = await evaluate(`
      const msgs = document.querySelectorAll('[class*="message"], [class*="Message"]');
      Array.from(msgs).map(m => m.textContent?.substring(0, 50)).join(' | ')
    `);
    console.log('   Messages in DOM:', messagesDebug || 'none found');

    // Step 4: Check for chips
    console.log('\n🔍 PASO 4: Buscando opciones de rol...');
    const chips = await evaluate(`
      Array.from(document.querySelectorAll('button'))
        .filter(b => ['Médico General', 'Especialista', 'Enfermera'].some(t => b.textContent.includes(t)))
        .map(b => b.textContent.trim())
        .join(' | ')
    `);
    console.log('   Chips:', chips || 'ninguno');

    if (chips) {
      // Step 5: Select role
      console.log('\n👆 PASO 5: Seleccionando "Médico General"...');
      await evaluate(`
        Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('Médico General'))
          ?.click()
      `);
      await sleep(6000);
      await takeScreenshot('04-after-role');

      // Step 6: Select clinic type
      console.log('\n👆 PASO 6: Seleccionando "Privada"...');
      await evaluate(`
        Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('Privada'))
          ?.click()
      `);
      await sleep(6000);
      await takeScreenshot('05-after-clinic');

      // Step 7: Select consultations
      console.log('\n👆 PASO 7: Seleccionando "6-15"...');
      await evaluate(`
        Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('6-15'))
          ?.click()
      `);
      await sleep(6000);
      await takeScreenshot('06-after-consults');
    }

    // Final screenshot
    await takeScreenshot('07-final');

    // Check state
    const state = await evaluate(`
      JSON.stringify({
        url: window.location.href,
        messageCount: document.querySelectorAll('[class*="message"]').length,
        hasComplete: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Completar'))
      })
    `);
    console.log('\n📊 Estado final:', state);

    console.log('\n✅ ¡Test completado!');
    console.log(`   Screenshots en: ${SCRATCHPAD}`);

  } finally {
    ws.close();
  }
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
