// @vitest-environment node
import { describe, it, expect } from 'vitest';
import postcss, { type AtRule, type Root } from 'postcss';
import tailwindcss from 'tailwindcss';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { FI_MOBILE_BREAKPOINT_PX, FI_MOBILE_QUERY } from 'fi-glass/theme';

const WEB = join(__dirname, '..', '..');

async function generatedUtilities(): Promise<Root> {
  const config = require(join(WEB, 'tailwind.config.js'));
  const result = await postcss([tailwindcss(config)]).process('@tailwind utilities;', {
    from: join(WEB, 'app', 'globals.css'),
  });
  return result.root;
}

function mediaOf(root: Root, selectorPart: string): string[] {
  const found: string[] = [];
  root.walkRules((rule) => {
    if (!rule.selector.includes(selectorPart)) return;
    const parent = rule.parent as AtRule | undefined;
    const isMedia = parent?.type === 'atrule' && parent.name.startsWith('media');
    found.push(isMedia ? `${parent.name.slice('media'.length)}${parent.params}`.replace(/\s+/g, '') : '');
  });
  return found;
}

describe('og118 compiles the classes fi-glass ships in its dist', () => {
  it('generates the mobile message utilities under the canonical query, not Tailwind md', async () => {
    const root = await generatedUtilities();
    const canonical = FI_MOBILE_QUERY.replace(/\s+/g, '');
    const indentReset = mediaOf(root, ':pl-0');
    expect(indentReset, 'fi-glass mobile indent reset was not generated').not.toHaveLength(0);
    expect(new Set(indentReset)).toEqual(new Set([canonical]));
    expect(mediaOf(root, 'max-md\\:')).toEqual([]);
  }, 30_000);
});

describe('og118 stylesheets switch at the same width as the fi-glass shell', () => {
  it('every max-width media query in globals.css is the canonical breakpoint', () => {
    const css = readFileSync(join(WEB, 'app', 'globals.css'), 'utf8');
    const widths = [...css.matchAll(/@media[^{]*max-width:\s*(\d+)px/g)].map(([, px]) => Number(px));
    expect(widths.length).toBeGreaterThan(0);
    expect(widths.filter((px) => px !== FI_MOBILE_BREAKPOINT_PX)).toEqual([]);
  });
});
