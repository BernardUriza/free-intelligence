// @vitest-environment node
import { describe, it, expect } from 'vitest';
import postcss from 'postcss';
import tailwindcss from 'tailwindcss';
import { join } from 'node:path';

const WEB = join(__dirname, '..', '..');

async function generatedUtilities(): Promise<string> {
  const config = require(join(WEB, 'tailwind.config.js'));
  const result = await postcss([tailwindcss(config)]).process('@tailwind utilities;', {
    from: join(WEB, 'app', 'globals.css'),
  });
  return result.css;
}

describe('og118 compiles the classes fi-glass ships in its dist', () => {
  it('generates a message-row utility that only fi-glass uses', async () => {
    const css = await generatedUtilities();
    expect(css).toContain('.max-md\\:pl-0');
  }, 30_000);
});
