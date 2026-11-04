import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const SRC = join(__dirname, '..');
const GREEN = /\b(?:[a-z-]+:)*(?:text|bg|border|ring|fill|stroke)-(?:emerald|green)-\d{2,3}(?:\/\d+)?\b/g;

const SUCCESS_ONLY = new Set([
  'agent/PlanChecklist.tsx',
  'agent/StepsPanel.tsx',
  'shell/ChatFilePreview.tsx',
  'voice/AudioQueueItem.tsx',
  'voice/VoiceMicButton.tsx',
]);

const withoutComments = (code: string) =>
  code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe('the consumer owns the accent', () => {
  it('hardcodes green only where it means success, never as the brand', () => {
    const offenders = sources(SRC)
      .map((path) => ({ file: relative(SRC, path), hits: withoutComments(readFileSync(path, 'utf8')).match(GREEN) ?? [] }))
      .filter(({ file, hits }) => hits.length > 0 && !SUCCESS_ONLY.has(file));
    expect(offenders).toEqual([]);
  });
});
