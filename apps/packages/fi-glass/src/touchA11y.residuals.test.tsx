// @vitest-environment jsdom

// FIGLASS-TOUCH-A11Y-1: jsdom does not lay out, so these pin the contracts; the
// 44px measurements were taken in real Chrome at 374/304px (see the backlog card).

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { TurnErrorBanner } from './agent/conversation-surface/components/transcript/TurnErrorBanner';
import { CollapsibleText } from './messages/CollapsibleText';
import { PersonaSelector } from './persona-selector/PersonaSelector';
import { ActionMenu } from './menu/ActionMenu';
import { ResourceListItems, ResourceListRow } from './resource/ResourceListSection';
import { ComposerFrame } from './composer/ComposerFrame';
import { AgentWorkspaceShell } from './agent/AgentWorkspaceShell';
import { ItemActionSlot } from './agent/AgentSidebarItem';
import { ComposerActionSlot } from './composer/ComposerActionSlot';
import { ensureSidebarItemStyle } from './agent/sidebarItemStyle';
import { ensureMessageActionsStyle } from './messages/messageActionsStyle';
import { FI_TOUCH_QUERY } from './theme/breakpoints';
import { clearMediaQueryCache } from './shell/useMediaQuery';

const TOUCH_SHEET = 'fi-touch-target-style';

function resetHead() {
  document.head.querySelectorAll('style').forEach((s) => s.remove());
}

function sheet(id: string): string {
  return document.getElementById(id)?.textContent ?? '';
}

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

beforeEach(() => {
  resetHead();
  clearMediaQueryCache();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('item 1 — every control below 44px composes fi-touch-target and injects its own sheet', () => {
  it('TurnErrorBanner retry and dismiss', () => {
    const { getByText } = render(
      <TurnErrorBanner error={{ message: 'x' }} onRetry={() => {}} onDismiss={() => {}} />,
    );
    expect(getByText('Reintentar').className).toContain('fi-touch-target');
    expect(getByText('Descartar').className).toContain('fi-touch-target');
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
  });

  it('TurnErrorBanner keeps the minimum when the consumer dresses the buttons', () => {
    const { getByText } = render(
      <TurnErrorBanner
        error={{ message: 'x' }}
        onRetry={() => {}}
        onDismiss={() => {}}
        retryButtonClassName="mine"
        dismissButtonClassName="theirs"
      />,
    );
    expect(getByText('Reintentar').className).toBe('fi-touch-target mine');
    expect(getByText('Descartar').className).toBe('fi-touch-target theirs');
  });

  it('CollapsibleText "show more" toggle', () => {
    const desc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollHeight');
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { configurable: true, get: () => 900 });
    try {
      const { getByRole } = render(<CollapsibleText maxHeight={100}>long</CollapsibleText>);
      expect(getByRole('button').className).toContain('fi-touch-target');
      expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
    } finally {
      if (desc) Object.defineProperty(HTMLElement.prototype, 'scrollHeight', desc);
    }
  });

  it('PersonaSelector trigger, also with a consumer trigger class', () => {
    const { getByRole } = render(
      <PersonaSelector
        personas={[{ id: 'a' }]}
        selected="a"
        onSelect={() => {}}
        getPersonaId={(p) => p.id}
        triggerClassName="og-trigger"
      />,
    );
    expect(getByRole('button').className).toBe('fi-touch-target og-trigger');
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
  });

  it('PersonaSelector footer close() hands focus back to the trigger, so a sheet it opens can return there', () => {
    const { getByRole } = render(
      <PersonaSelector
        personas={[{ id: 'a' }]}
        selected="a"
        onSelect={() => {}}
        getPersonaId={(p) => p.id}
        renderFooter={({ close }) => (
          <button type="button" onClick={close}>
            Nuevo
          </button>
        )}
      />,
    );
    const trigger = getByRole('button');
    fireEvent.click(trigger);
    const action = getByRole('button', { name: 'Nuevo' });
    action.focus();
    fireEvent.click(action);
    expect(document.activeElement).toBe(trigger);
  });

  it('ActionMenu items, also with a consumer item class', () => {
    const { getByRole, getAllByRole } = render(
      <ActionMenu
        trigger="+"
        triggerLabel="Añadir"
        actions={[
          { id: 'a', label: 'Uno', onSelect: () => {} },
          { id: 'b', label: 'Dos', onSelect: () => {}, className: 'danger' },
        ]}
      />,
    );
    fireEvent.click(getByRole('button', { name: 'Añadir' }));
    const items = getAllByRole('menuitem');
    expect(items[0].className).toContain('fi-touch-target');
    expect(items[1].className).toBe('fi-touch-target danger');
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
  });

  it('ItemActionSlot and ComposerActionSlot inject the sheet they depend on', () => {
    render(
      <ItemActionSlot label="Borrar" onActivate={() => {}}>
        x
      </ItemActionSlot>,
    );
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
    cleanup();
    resetHead();
    render(<ComposerActionSlot aria-label="Enviar" icon="s" />);
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
  });

  it('ResourceListRow', () => {
    const { getByRole } = render(
      <ResourceListItems>
        <ResourceListRow title="t" meta="m" />
      </ResourceListItems>,
    );
    expect(getByRole('button').className).toContain('fi-touch-target');
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
  });
});

describe('item 2 — the rail toggle is 44px in a narrow composer on a wide screen', () => {
  it('ComposerFrame injects the touch sheet itself and sizes the toggle by container', () => {
    render(
      <ComposerFrame footerStart={<span>chip</span>}>
        <textarea />
      </ComposerFrame>,
    );
    expect(document.getElementById(TOUCH_SHEET)).not.toBeNull();
    const css = sheet('fi-composer-frame-style');
    const container = css.slice(css.indexOf('@container fi-composer (max-width: 420px)'));
    expect(container).toMatch(
      /\.fi-composer-rail-toggle \{[^}]*min-width: var\(--fi-touch-target, 44px\);[^}]*min-height: var\(--fi-touch-target, 44px\);/,
    );
  });
});

describe('item 3 — a sidebar action is revealed wherever it is sized to 44', () => {
  it('the reveal and the wrap share the touch gate (coarse pointer OR <=768)', () => {
    ensureSidebarItemStyle();
    const css = sheet('fi-sidebar-item-style');
    expect(css).not.toContain('@media (pointer: coarse) {');
    const block = css.slice(css.indexOf(`@media ${FI_TOUCH_QUERY} {`));
    expect(css).toContain(`@media ${FI_TOUCH_QUERY} {`);
    expect(block).toMatch(/\.fi-item-action \{\s*opacity: 1;/);
    expect(block).toMatch(/\.fi-sidebar-item \{\s*flex-wrap: wrap;/);
  });
});

describe('item 5 — per-message actions on touch stay reachable by keyboard and screen reader', () => {
  it('collapsed actions are visually hidden, never display:none, and reveal on focus', () => {
    ensureMessageActionsStyle();
    const css = sheet('fi-msg-actions-style');
    const coarse = css.slice(css.indexOf('@media (pointer: coarse)'));
    expect(coarse).not.toMatch(/\.fi-msg-actions \{\s*display: none;/);
    expect(coarse).toMatch(/clip-path: inset\(50%\)/);
    expect(coarse).toContain('.fi-msg-actions:focus-within');
  });
});

describe('item 4 — the drawer is a modal dialog that owns focus', () => {
  function renderDrawer() {
    mockMatchMedia(true);
    return render(
      <AgentWorkspaceShell
        responsive
        toggleLabel="Conversaciones"
        sidebar={(api) => (
          <button type="button" onClick={api.close}>
            Nuevo chat
          </button>
        )}
        conversation={<div>chat</div>}
      />,
    );
  }

  it('opening moves focus into the panel', () => {
    const { container, getByRole } = renderDrawer();
    const toggle = container.querySelector('.fi-aws-toggle') as HTMLButtonElement;
    toggle.focus();
    act(() => toggle.click());
    expect(document.activeElement).toBe(getByRole('dialog'));
  });

  it('the panel is role=dialog + aria-modal while in drawer mode, the nav stays a labelled landmark', () => {
    const { getByRole } = renderDrawer();
    const dialog = getByRole('dialog', { hidden: true });
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-label')).toBe('Conversaciones');
    expect(dialog.querySelector('nav[aria-label="Conversaciones"]')).not.toBeNull();
  });

  it('the toggle stays mounted, reports aria-expanded truthfully, and gets focus back on close', () => {
    const { container, getByText } = renderDrawer();
    const toggle = container.querySelector('.fi-aws-toggle') as HTMLButtonElement;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    toggle.focus();
    act(() => toggle.click());
    expect(container.querySelector('.fi-aws-toggle')).toBe(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    act(() => {
      fireEvent.keyDown(document, { key: 'Escape' });
    });
    expect(document.activeElement).toBe(toggle);
    act(() => toggle.click());
    act(() => getByText('Nuevo chat').click());
    expect(document.activeElement).toBe(toggle);
  });

  it('the page behind the open drawer is inert', () => {
    const { container } = renderDrawer();
    const page = container.querySelector('[data-fi-workspace="agent"]') as HTMLElement;
    expect(page.hasAttribute('inert')).toBe(false);
    act(() => (container.querySelector('.fi-aws-toggle') as HTMLButtonElement).click());
    expect(page.hasAttribute('inert')).toBe(true);
  });

  it('the panel owns the bottom and left safe areas so no consumer has to patch them', () => {
    const assigned: Record<string, string> = {};
    const proto = Object.getPrototypeOf(document.body.style);
    for (const prop of ['paddingBottom', 'paddingLeft']) {
      const desc = Object.getOwnPropertyDescriptor(proto, prop);
      vi.spyOn(proto, prop, 'set').mockImplementation(function (this: CSSStyleDeclaration, v: string) {
        if (String(v).startsWith('env(')) assigned[prop] = v;
        desc?.set?.call(this, v);
      });
    }
    renderDrawer();
    expect(assigned.paddingBottom).toBe('env(safe-area-inset-bottom, 0px)');
    expect(assigned.paddingLeft).toBe('env(safe-area-inset-left, 0px)');
  });
});

describe('item 6 — popovers stay inside a 320px viewport', () => {
  const VIEWPORT = 320;
  let innerWidth: PropertyDescriptor | undefined;

  beforeEach(() => {
    innerWidth = Object.getOwnPropertyDescriptor(window, 'innerWidth');
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: VIEWPORT });
  });
  afterEach(() => {
    if (innerWidth) Object.defineProperty(window, 'innerWidth', innerWidth);
  });

  function rectAt(left: number, width: number): DOMRect {
    return { left, right: left + width, width, top: 600, bottom: 644, height: 44, x: left, y: 600, toJSON: () => ({}) } as DOMRect;
  }

  it('ActionMenu opened from a trigger near the right edge is shifted back inside', () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      return this.getAttribute('role') === 'menu' ? rectAt(Number.parseFloat(this.style.left) || 0, 208) : rectAt(200, 44);
    });
    const { getByRole } = render(
      <ActionMenu trigger="+" triggerLabel="Añadir" actions={[{ id: 'a', label: 'Uno', onSelect: () => {} }]} />,
    );
    fireEvent.click(getByRole('button', { name: 'Añadir' }));
    const menu = getByRole('menu');
    expect(menu.style.maxWidth).toBe('calc(100vw - 16px)');
    const left = Number.parseFloat(menu.style.left);
    expect(left + 208).toBeLessThanOrEqual(VIEWPORT - 8);
    expect(left).toBeGreaterThanOrEqual(8);
  });

  it('PersonaSelector caps its panel to the viewport and clamps it horizontally', async () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      return this.getAttribute('role') === 'listbox' ? rectAt(Number.parseFloat(this.style.left) || 0, 304) : rectAt(60, 250);
    });
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0);
      return 0;
    });
    const { getByRole } = render(
      <PersonaSelector personas={[{ id: 'a' }]} selected="a" onSelect={() => {}} getPersonaId={(p) => p.id} />,
    );
    fireEvent.click(getByRole('button'));
    const listbox = getByRole('listbox');
    expect(listbox.style.maxWidth).toBe('calc(100vw - 16px)');
    const left = Number.parseFloat(listbox.style.left);
    expect(left + 304).toBeLessThanOrEqual(VIEWPORT - 8);
  });
});
