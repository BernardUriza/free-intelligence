import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ChatMessage } from '@free-intelligence/core';
import { Og118MessageActions } from '../Og118MessageActions';

const TS = '2026-06-09T00:00:00.000Z';
const assistantMsg: ChatMessage = {
  role: 'assistant',
  content: 'respuesta del asistente',
  timestamp: TS,
};
const userMsg: ChatMessage = { role: 'user', content: 'pregunta del usuario', timestamp: TS };

describe('Og118MessageActions', () => {
  it('keeps Copy and ADDS Speak on assistant messages', () => {
    render(<Og118MessageActions message={assistantMsg} currentVoice="nova" onSpeak={vi.fn()} />);
    // Copy preserved (B3-TTS-1 must not break copy).
    expect(screen.getByRole('button', { name: /copiar mensaje/i })).toBeInTheDocument();
    // Speak added.
    expect(screen.getByRole('button', { name: /escuchar mensaje/i })).toBeInTheDocument();
  });

  it('shows Copy but NOT Speak on user messages', () => {
    render(<Og118MessageActions message={userMsg} currentVoice="nova" onSpeak={vi.fn()} />);
    expect(screen.getByRole('button', { name: /copiar mensaje/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /escuchar mensaje/i })).toBeNull();
  });

  it('fires onSpeak with the message content and current voice when Speak is clicked', async () => {
    const onSpeak = vi.fn();
    render(<Og118MessageActions message={assistantMsg} currentVoice="shimmer" onSpeak={onSpeak} />);
    await userEvent.click(screen.getByRole('button', { name: /escuchar mensaje/i }));
    expect(onSpeak).toHaveBeenCalledWith('respuesta del asistente', 'shimmer', false);
  });
});
