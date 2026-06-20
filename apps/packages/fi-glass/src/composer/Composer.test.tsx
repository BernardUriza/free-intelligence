// @vitest-environment jsdom
/**
 * Tests for Composer — Enter-to-send keyboard contract.
 *
 * Daily-driver audit (2026-06-11) reported "Enter does not send" on staging.
 * These tests pin the chat convention at the framework layer, interactively
 * (jsdom + user-event, not SSR): Enter sends and does NOT insert a newline;
 * Shift+Enter inserts a newline and does NOT send.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { Composer } from './Composer';

function Harness({ onSend }: { onSend: () => void }) {
  const [message, setMessage] = useState('');
  return (
    <Composer
      message={message}
      onMessageChange={setMessage}
      onSend={onSend}
      placeholder="escribe aquí"
    />
  );
}

describe('<Composer> Enter-to-send', () => {
  afterEach(cleanup);

  it('sends on Enter and does not insert a newline', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<Harness onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('escribe aquí');
    await user.type(textarea, 'hola og118');
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledTimes(1);
    expect((textarea as HTMLTextAreaElement).value).toBe('hola og118');
    expect((textarea as HTMLTextAreaElement).value).not.toContain('\n');
  });

  it('inserts a newline on Shift+Enter and does not send', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<Harness onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('escribe aquí');
    await user.type(textarea, 'línea uno');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    await user.type(textarea, 'línea dos');

    expect(onSend).not.toHaveBeenCalled();
    expect((textarea as HTMLTextAreaElement).value).toBe('línea uno\nlínea dos');
  });

  it('still calls onSend on Enter while empty (guard lives in the consumer)', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<Harness onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('escribe aquí');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledTimes(1);
    expect((textarea as HTMLTextAreaElement).value).toBe('');
  });
});

describe('<Composer> accessibility metadata (B3-FIGLASS-A11Y-1)', () => {
  afterEach(cleanup);

  it('renders a textarea with a default id and name (no form-field warning)', () => {
    render(
      <Composer
        message=""
        onMessageChange={() => {}}
        onSend={() => {}}
        placeholder="escribe aquí"
      />,
    );
    const textarea = screen.getByPlaceholderText('escribe aquí') as HTMLTextAreaElement;
    expect(textarea.id).toBeTruthy();
    expect(textarea.getAttribute('name')).toBeTruthy();
  });

  it('forwards consumer-provided id and name to the textarea', () => {
    render(
      <Composer
        message=""
        onMessageChange={() => {}}
        onSend={() => {}}
        placeholder="escribe aquí"
        id="og118-composer"
        name="og118-message"
      />,
    );
    const textarea = screen.getByPlaceholderText('escribe aquí') as HTMLTextAreaElement;
    expect(textarea.id).toBe('og118-composer');
    expect(textarea.getAttribute('name')).toBe('og118-message');
  });
});
