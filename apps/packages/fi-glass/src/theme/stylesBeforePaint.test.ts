import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const SRC = join(__dirname, '..');
const INJECT_IN_EFFECT = /useEffect\(\(\) => (?:\{\s*(?:if \(\w+\) )?)?ensure\w+Style\(\)/;

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe('styles land before the first paint', () => {
  it('injects every stylesheet in useInsertionEffect, never in useEffect (CLS 0.29 measured on og118)', () => {
    const offenders = sources(SRC)
      .filter((path) => INJECT_IN_EFFECT.test(readFileSync(path, 'utf8')))
      .map((path) => relative(SRC, path));
    expect(offenders).toEqual([]);
  });
});
