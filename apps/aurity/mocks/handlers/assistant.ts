// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse, ws } from 'msw';
import { assistantChat, assistantGreeting, historySearchResponse } from '@/mocks/fixtures/assistant';
import { sse } from '@/mocks/utils/sse';

export const assistantHandlers = [
  http.post('/api/aurity/assistant/chat', async ({ request }) => {
    const body = await request.json();
    const isIntro = Array.isArray(body?.messages) && body.messages.some((m: any) => m.role === 'system');
    if (isIntro) {
      return HttpResponse.json({
        id: 'chat-intro-1',
        choices: [{ message: { role: 'assistant', content: assistantGreeting.message }, finish_reason: 'stop' }],
        persona: assistantGreeting.persona,
      });
    }

    return HttpResponse.json({
      id: 'chat-1',
      persona: assistantChat.persona,
      thinking: assistantChat.thinking,
      emotional_analysis: assistantChat.emotional_analysis,
      choices: [
        {
          message: { role: 'assistant', content: assistantChat.message },
          finish_reason: 'stop',
        },
      ],
    });
  }),

  http.post('/api/aurity/assistant/chat/stream', async ({ request }) => {
    await request.json();
    return sse([
      { event: 'meta', data: { thinking: assistantChat.thinking } },
      { data: { choices: [{ delta: { content: 'He registrado la indicación ' } }] } },
      { data: { choices: [{ delta: { content: 'en la nota SOAP y órdenes.' } }] } },
      {
        data: {
          id: 'stream-1',
          choices: [
            {
              message: { role: 'assistant', content: assistantChat.message },
              finish_reason: 'stop',
            },
          ],
          persona: assistantChat.persona,
          thinking: assistantChat.thinking,
        },
      },
      { data: '[DONE]' },
    ]);
  }),

  http.post('/api/aurity/assistant/history/search', () => {
    return HttpResponse.json(historySearchResponse);
  }),

  // WebSocket handlers for both ws:// (dev) and wss:// (prod)
  ws.link('ws://*/api/aurity/assistant/ws', {
    onConnect(_, client) {
      client.send({ type: 'connected', timestamp: Date.now() });
      client.send({
        type: 'new_message',
        role: 'assistant',
        content: assistantGreeting.message,
        timestamp: Date.now(),
      });
    },
    onMessage(_, client, message) {
      if (message === 'ping') {
        client.send({ type: 'pong', timestamp: Date.now() });
      }
    },
  }),
  ws.link('wss://*/api/aurity/assistant/ws', {
    onConnect(_, client) {
      client.send({ type: 'connected', timestamp: Date.now() });
      client.send({
        type: 'new_message',
        role: 'assistant',
        content: assistantGreeting.message,
        timestamp: Date.now(),
      });
    },
    onMessage(_, client, message) {
      if (message === 'ping') {
        client.send({ type: 'pong', timestamp: Date.now() });
      }
    },
  }),
];
