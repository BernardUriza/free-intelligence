/**
 * fi-glass must not learn the consumer's noun — the surface layer.
 *
 * The card's hard rule: "las primitivas suben a fi-glass como patrón genérico de
 * 'resource workspace' (fi-glass NO conoce la palabra 'project' — og118 la
 * mapea)". A rule stated only in prose is a rule that drifts — the first
 * `newProjectLabel` prop added in a hurry would pass review because nothing
 * checks. This reads the source and fails on the noun.
 *
 * Comments and doc blocks are stripped before checking: the docs are allowed to
 * SAY that og118 renders projects with these. What is forbidden is a project
 * living in the API — a prop, a type, a default string a consumer cannot change.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const DIR = __dirname;

/**
 * Strip what is allowed to contain a noun-shaped word:
 *
 * - comments — the docs MAY say that og118 renders projects with these; what is
 *   forbidden is a project living in the API;
 * - `--glass-chat-*` and `glassTokens.*` — the framework's OWN theme namespace.
 *   `--glass-chat-text` is a design token every fi-glass module reads; it is not
 *   the consumer's vocabulary leaking in, and a guard that flagged it would be
 *   trained away as noise within a week.
 */
function code(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '')
    .replace(/--glass-chat-[a-z-]+/g, '')
    .replace(/glassTokens\.[A-Za-z]+/g, '')
    .replace(/glass-chat\.css|glassTheme/g, '');
}

/**
 * NO `\b` word boundaries, on purpose. The first version used them and a mutation
 * proved it toothless: `newProjectLabel` has no boundary before `Project`, so the
 * exact prop this guard exists to reject sailed through green. camelCase is how a
 * product noun actually enters an API, so the match must be a plain substring.
 */
const FORBIDDEN = /(project|proyecto|conversacion|conversation|chat|corpus)/i;

describe('the surface primitives stay free of the consumer vocabulary', () => {
  const sources = readdirSync(DIR).filter(
    (f) => (f.endsWith('.ts') || f.endsWith('.tsx')) && !f.includes('.test.'),
  );

  /*
   * The guard's real enemy is a rename that leaves it scanning nothing and
   * still green. A count alone is a weak fence — it drifts every time a
   * component is added — so this names the files that MUST be under the guard.
   * Adding a component to the module does not touch this list; deleting or
   * renaming one of these does, which is exactly when a human should look.
   */
  it('scans the module (a rename must not silently empty this guard)', () => {
    expect(sources).toEqual(
      expect.arrayContaining(['Surface.tsx', 'surfaceStyle.ts']),
    );
  });

  for (const file of sources) {
    it(`${file} names no product noun in its code`, () => {
      const offending = code(readFileSync(join(DIR, file), 'utf8'))
        .split('\n')
        .map((line, i) => [i + 1, line] as const)
        .filter(([, line]) => FORBIDDEN.test(line));

      expect(
        offending.map(([n, l]) => `${n}: ${l.trim()}`),
        'a product noun in the API means the next consumer inherits og118 vocabulary',
      ).toEqual([]);
    });
  }
});
