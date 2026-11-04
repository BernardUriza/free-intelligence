import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { builtinModules, createRequire } from 'node:module';
import { join } from 'node:path';
import { messageStyles } from './messages/styles';

const ROOT = join(__dirname, '..');
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
const require = createRequire(import.meta.url);

function sourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) sourceFiles(full, acc);
    else if (/\.(ts|tsx)$/.test(entry.name)) acc.push(full);
  }
  return acc;
}

function jsFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) jsFiles(full, acc);
    else if (/\.m?js$/.test(entry.name)) acc.push(full);
  }
  return acc;
}

function packageOf(specifier: string): string {
  const parts = specifier.split('/');
  return specifier.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
}

describe('fi-glass declares what it uses', () => {
  it('every package imported from src — tests included — is a declared dependency', () => {
    const declared = new Set([
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.devDependencies ?? {}),
      ...Object.keys(pkg.peerDependencies ?? {}),
    ]);
    const undeclared = new Set<string>();
    for (const file of sourceFiles(join(ROOT, 'src'))) {
      const src = readFileSync(file, 'utf8');
      const specifiers = [
        ...src.matchAll(/^\s*(?:import|export)\s[^'"]*?\bfrom\s+['"]([^'".][^'"]*)['"]/gm),
        ...src.matchAll(/^\s*import\s+['"]([^'".][^'"]*)['"]/gm),
        ...src.matchAll(/\bimport\(\s*['"]([^'".][^'"]*)['"]\s*\)/g),
      ].map((match) => match[1]);
      for (const spec of specifiers) {
        const name = packageOf(spec);
        if (spec.startsWith('node:') || builtinModules.includes(name)) continue;
        if (!declared.has(name)) undeclared.add(`${name} (${file.replace(ROOT, '')})`);
      }
    }
    expect([...undeclared]).toEqual([]);
  });
});

describe('every JS subpath export is built and shipped', () => {
  const tsup = readFileSync(join(ROOT, 'tsup.config.ts'), 'utf8');
  const subpaths = Object.entries(pkg.exports as Record<string, { import?: string }>)
    .filter(([, target]) => typeof target === 'object' && target.import?.startsWith('./dist/'))
    .map(([key, target]) => ({ key, src: target.import!.replace('./dist/', 'src/').replace(/\.js$/, '.ts') }));

  it('includes the admin-kit, persona-admin and model-catalog subpaths', () => {
    expect(subpaths.map((s) => s.key)).toEqual(expect.arrayContaining(['./admin-kit', './persona-admin', './model-catalog']));
  });

  it.each(subpaths)('$key has a tsup entry and a built dist', ({ key, src }) => {
    expect(tsup).toContain(`'${src}'`);
    expect(readdirSync(join(ROOT, 'dist', key === '.' ? '' : key.slice(2)))).toContain('index.js');
  });
});

describe('the Tailwind contract is declared, not folklore', () => {
  it('exports fi-glass/tailwind and publishes the file behind it', () => {
    expect(pkg.exports['./tailwind']).toBeTruthy();
    expect(pkg.files).toContain('tailwind.cjs');
  });

  it('its content globs are the dist that carries the class strings', () => {
    const { content } = require(join(ROOT, 'tailwind.cjs')) as { content: string[] };
    const dist = join(ROOT, 'dist').split('\\').join('/');
    expect(content).toEqual([`${dist}/**/*.{js,mjs}`]);

    const scanned = jsFiles(join(ROOT, 'dist'));
    expect(scanned.some((file) => readFileSync(file, 'utf8').includes(messageStyles.content.base))).toBe(true);
  });
});

describe('the dist bundles each module once, with its client boundary', () => {
  const dist = () => jsFiles(join(ROOT, 'dist')).map((file) => ({ file, code: readFileSync(file, 'utf8') }));

  it('module state is not duplicated across subpaths: one useMediaQuery cache', () => {
    const owners = dist().filter(({ code }) => /\bmqlCache = (?:\/\*[^*]*\*\/ )?new Map\b/.test(code));
    expect(owners.map(({ file }) => file.replace(ROOT, ''))).toHaveLength(1);
  });

  it("every dist file that carries a 'use client' module opens with the directive", () => {
    const isClient = (srcPath: string) =>
      /^\s*['"]use client['"]/.test(readFileSync(join(ROOT, srcPath), 'utf8').replace(/^\s*(\/\/[^\n]*\n|\/\*[\s\S]*?\*\/)*/g, ''));
    const missing = dist()
      .filter(({ code }) => [...code.matchAll(/^\/\/ (src\/\S+\.tsx?)$/gm)].some(([, src]) => isClient(src)))
      .filter(({ code }) => !/^['"]use client['"]/.test(code))
      .map(({ file }) => file.replace(ROOT, ''));
    expect(missing).toEqual([]);
  });
});
