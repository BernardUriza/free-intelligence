// @vitest-environment jsdom
// A guarantee carries real specificity; a default the consumer may restyle sits in :where().

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { ensureTouchTargetStyle } from '../shell/touchTarget';
import { ensureResourceStyle } from '../resource/resourceStyle';
import { ensureComposerActionStyle } from '../composer/composerActionStyle';

const glassChatCss = readFileSync(join(__dirname, 'glass-chat.css'), 'utf8');
const injected = (id: string) => document.getElementById(id)?.textContent ?? '';
const ruleOf = (css: string, declaration: string) =>
  css.split(declaration)[0].split('\n').reverse().find((line) => line.includes('{')) ?? '';

beforeAll(() => {
  ensureTouchTargetStyle();
  ensureResourceStyle();
  ensureComposerActionStyle();
});

describe('fi-glass cascade contract', () => {
  it('lets a consumer class restyle the composer slots, even inside its @container', () => {
    for (const slot of ['area', 'footer', 'header']) {
      expect(glassChatCss).toContain(`:where(.glass-chat-composer [data-fi-composer-slot='${slot}'])`);
      expect(glassChatCss).not.toMatch(
        new RegExp(`^\\.glass-chat-composer \\[data-fi-composer-slot='${slot}'\\]`, 'm'),
      );
    }
  });

  it('guarantees the 44px touch minimum but only defaults the centering', () => {
    const css = injected('fi-touch-target-style');
    expect(ruleOf(css, 'min-height: var(--fi-touch-target, 44px)')).not.toContain(':where(');
    expect(ruleOf(css, 'align-items: center')).toContain(':where(');
    expect(ruleOf(css, 'display: inline-flex')).toContain(':where(');
  });

  it('cards declare their own layout so the touch centering never reaches them', () => {
    const css = injected('fi-resource-style');
    for (const card of ['.fi-resource-card {', '.fi-doc-card {']) {
      const block = css.slice(css.indexOf(card), css.indexOf('}', css.indexOf(card)));
      expect(block).toContain('align-items: stretch');
      expect(block).toContain('justify-content: flex-start');
    }
  });

  it('makes the area slot the compact row flexing member, so send sits at the row end', async () => {
    const { ensureComposerFrameStyle } = await import('../composer/ComposerFrame');
    ensureComposerFrameStyle();
    const compact = injected('fi-composer-frame-style').split('@container fi-composer (max-width: 420px)')[1];
    expect(compact).toContain('[data-fi-composer-frame] > [data-fi-composer-slot="area"]');
  });

  it('a resource card loads the touch sheet its class depends on', () => {
    document.getElementById('fi-touch-target-style')?.remove();
    document.getElementById('fi-resource-style')?.remove();
    ensureResourceStyle();
    expect(document.getElementById('fi-touch-target-style')).not.toBeNull();
  });

  it('keeps the disabled cursor above the preflight :disabled reset', () => {
    const css = injected('fi-composer-action-style');
    expect(ruleOf(css, 'cursor: not-allowed')).toContain('.fi-composer-action:disabled');
    expect(ruleOf(css, 'cursor: not-allowed')).not.toContain(':where(');
  });
});
