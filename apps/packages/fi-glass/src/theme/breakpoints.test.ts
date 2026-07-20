import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { FI_MOBILE_BREAKPOINT_PX, FI_MOBILE_QUERY, FI_TOUCH_QUERY } from './breakpoints';

const SRC = join(__dirname, '..');

function readAll(dir: string, ext: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) readAll(full, ext, acc);
    else if (entry.name.endsWith(ext)) acc.push(full);
  }
  return acc;
}

describe('the mobile breakpoint has exactly one source of truth', () => {
  it('every max-width in the hand-written stylesheets equals the constant', () => {
    const offenders: string[] = [];
    for (const file of readAll(SRC, '.css')) {
      const css = readFileSync(file, 'utf8');
      for (const [, px] of css.matchAll(/@media[^{]*max-width:\s*(\d+)px/g)) {
        if (Number(px) !== FI_MOBILE_BREAKPOINT_PX) {
          offenders.push(`${file.replace(SRC, 'src')} → ${px}px`);
        }
      }
    }
    // A static .css cannot read the TS constant (a media query cannot resolve a
    // custom property), so THIS is the joint that holds them together. If you
    // change FI_MOBILE_BREAKPOINT_PX, update the stylesheets in the same commit.
    expect(offenders).toEqual([]);
  });

  it('no source file hardcodes the breakpoint instead of importing it', () => {
    const offenders: string[] = [];
    for (const file of [...readAll(SRC, '.ts'), ...readAll(SRC, '.tsx')]) {
      if (file.endsWith('breakpoints.ts') || file.includes('.test.')) continue;
      const src = readFileSync(file, 'utf8');
      // Only flag it inside an actual media query / width comparison, so prose
      // in a comment or an unrelated 768 never trips this.
      if (/max-width:\s*768px/.test(src)) {
        offenders.push(file.replace(SRC, 'src'));
      }
    }
    expect(offenders).toEqual([]);
  });

  it('exposes the queries the sheets and hooks consume', () => {
    expect(FI_MOBILE_QUERY).toBe('(max-width: 768px)');
    expect(FI_TOUCH_QUERY).toBe('(pointer: coarse), (max-width: 768px)');
  });
});
