// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest';
import { ensureDensityStyle } from './densityStyle';

const STYLE_ID = 'fi-density-style';

afterEach(() => {
  document.getElementById(STYLE_ID)?.remove();
});

describe('B3-FIGLASS-UX-TOKENS-1 · density/spacing contract', () => {
  it('injects the stylesheet once (idempotent)', () => {
    ensureDensityStyle();
    ensureDensityStyle();
    expect(document.querySelectorAll(`#${STYLE_ID}`)).toHaveLength(1);
  });

  it('defines the base spacing scale on the workspace root', () => {
    ensureDensityStyle();
    const css = document.getElementById(STYLE_ID)!.textContent!;
    for (const step of ['--fi-space-1', '--fi-space-2', '--fi-space-3', '--fi-space-4', '--fi-space-5']) {
      expect(css).toContain(step);
    }
    expect(css).toContain('--fi-touch-target: 44px');
    expect(css).toContain('--fi-radius-section');
  });

  it('exposes the three density variants', () => {
    ensureDensityStyle();
    const css = document.getElementById(STYLE_ID)!.textContent!;
    expect(css).toContain('.fi-density-compact');
    expect(css).toContain('.fi-density-comfortable');
    expect(css).toContain('.fi-density-spacious');
  });

  it('comfortable (the default) reproduces the previous hardcoded values exactly (backward-compat)', () => {
    ensureDensityStyle();
    const css = document.getElementById(STYLE_ID)!.textContent!;
    const comfortable = css.slice(css.indexOf('.fi-density-comfortable'), css.indexOf('.fi-density-compact'));
    // these are the literals the section/item primitives shipped before this PR
    expect(comfortable).toContain('--fi-item-gap: 0.4rem');
    expect(comfortable).toContain('--fi-item-padding: 0.55rem 0.6rem');
    expect(comfortable).toContain('--fi-section-head-gap: 0.5rem');
    expect(comfortable).toContain('--fi-section-head-padding: 0.8rem 0.85rem 0.5rem');
  });
});
