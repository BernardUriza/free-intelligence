// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { ConversationSummary } from '@free-intelligence/core';
import { readConversationIdFromPath, useConversationUrl } from './useConversationUrl';

const NOW = '2026-10-09T12:00:00.000Z';
const chat = (id: string): ConversationSummary => ({ id, title: id, createdAt: NOW, updatedAt: NOW, preview: '' });

type Props = { activeId: string | null; conversations: ConversationSummary[] };

function mount(initial: Props, onNavigate = vi.fn()) {
  const hook = renderHook((p: Props) => useConversationUrl({ ...p, onNavigate }), { initialProps: initial });
  return { ...hook, onNavigate };
}

beforeEach(() => window.history.replaceState(null, '', '/'));

describe('readConversationIdFromPath', () => {
  it('reads /c/<id> with or without the trailing slash, and nothing else', () => {
    expect(readConversationIdFromPath('/c/abc')).toBe('abc');
    expect(readConversationIdFromPath('/c/abc/')).toBe('abc');
    expect(readConversationIdFromPath('/')).toBeNull();
    expect(readConversationIdFromPath('/projects/')).toBeNull();
    expect(readConversationIdFromPath('/c/a/b')).toBeNull();
  });
});

describe('useConversationUrl', () => {
  it('keeps a fresh chat at / and gives it /c/<id> in place once it is saved', () => {
    const { rerender } = mount({ activeId: 'fresh', conversations: [] });
    expect(window.location.pathname).toBe('/');
    const length = window.history.length;
    rerender({ activeId: 'fresh', conversations: [chat('fresh')] });
    expect(window.location.pathname).toBe('/c/fresh');
    expect(window.history.length).toBe(length);
  });

  it('from a fresh chat at /, opening a saved chat pushes history so Back returns to /', () => {
    const { rerender } = mount({ activeId: 'fresh', conversations: [chat('a')] });
    expect(window.location.pathname).toBe('/');
    const length = window.history.length;
    rerender({ activeId: 'a', conversations: [chat('a')] });
    expect(window.location.pathname).toBe('/c/a');
    expect(window.history.length).toBe(length + 1);
  });

  it('pushes history when switching chats and goes back to / for a new one', () => {
    const { rerender } = mount({ activeId: 'a', conversations: [chat('a'), chat('b')] });
    expect(window.location.pathname).toBe('/c/a');
    const length = window.history.length;
    rerender({ activeId: 'b', conversations: [chat('a'), chat('b')] });
    expect(window.location.pathname).toBe('/c/b');
    rerender({ activeId: 'new', conversations: [chat('a'), chat('b')] });
    expect(window.location.pathname).toBe('/');
    expect(window.history.length).toBe(length + 2);
  });

  it('does not wipe /c/<id> while the list is still loading', () => {
    window.history.replaceState(null, '', '/c/a');
    const { rerender } = mount({ activeId: 'a', conversations: [] });
    expect(window.location.pathname).toBe('/c/a');
    rerender({ activeId: 'a', conversations: [chat('a')] });
    expect(window.location.pathname).toBe('/c/a');
  });

  it('back/forward opens the chat the address names', () => {
    const { onNavigate } = mount({ activeId: 'a', conversations: [chat('a')] });
    act(() => {
      window.history.pushState(null, '', '/c/b');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(onNavigate).toHaveBeenLastCalledWith('b');
    act(() => {
      window.history.pushState(null, '', '/');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(onNavigate).toHaveBeenLastCalledWith(null);
  });
});
