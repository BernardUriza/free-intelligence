/**
 * Mock SSE backend for og118 local E2E (DD-002B1.3). NO LLM, no credits, no
 * cloud — a deterministic stand-in for the fi-runner `/chat/stream` endpoint so
 * the conversation sidebar + local-first persistence can be driven in a real
 * browser without touching the real backend.
 *
 * Emits fi-runner's NATIVE frame shape (open / plan / text / result / done),
 * which useOg118Agent maps to core's AgentStreamEvent. The reply echoes the
 * user's message + session_id so the E2E can assert which thread it landed in.
 *
 * Run: node apps/og118/web/scripts/mock-sse-server.mjs   (listens on :8118)
 */

import { createServer } from 'node:http';

const PORT = Number(process.env.MOCK_SSE_PORT ?? 8118);

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

function sse(res, obj) {
  res.write(`data: ${JSON.stringify(obj)}\n\n`);
}

const server = createServer((req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, CORS);
    res.end();
    return;
  }
  if (req.method !== 'POST' || !req.url?.startsWith('/chat/stream')) {
    res.writeHead(404, CORS);
    res.end();
    return;
  }

  let body = '';
  req.on('data', (chunk) => {
    body += chunk;
  });
  req.on('end', () => {
    let message = '';
    let sessionId = '';
    try {
      const parsed = JSON.parse(body || '{}');
      message = String(parsed.message ?? '');
      sessionId = String(parsed.session_id ?? '');
    } catch {
      /* ignore malformed body */
    }

    res.writeHead(200, {
      ...CORS,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });

    const reply = `Echo: ${message} [session ${sessionId.slice(0, 8)}]`;

    // Deterministic glass-box turn: open → plan → streamed text → result → done.
    sse(res, { type: 'open' });
    sse(res, { type: 'plan', data: { steps: ['understand', 'answer'] } });
    sse(res, { type: 'step_started', data: { step_index: 0 } });
    sse(res, { type: 'step_done', data: { step_index: 0, status: 'done' } });
    sse(res, { type: 'step_started', data: { step_index: 1 } });
    for (const word of reply.split(' ')) {
      sse(res, { type: 'text', text: `${word} ` });
    }
    sse(res, { type: 'step_done', data: { step_index: 1, status: 'done' } });
    sse(res, { type: 'result', result: { text: reply } });
    sse(res, { type: 'done' });
    res.end();
  });
});

server.listen(PORT, () => {
  console.log(`[mock-sse] listening on http://localhost:${PORT}/chat/stream`);
});
