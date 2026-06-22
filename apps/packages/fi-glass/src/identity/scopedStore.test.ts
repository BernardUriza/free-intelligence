import { describe, it, expect } from 'vitest';

import { scopedStoreName } from './scopedStore';

describe('scopedStoreName', () => {
  it('NEVER resolves to the bare base — a null/empty identity maps to an explicit legacy scope', () => {
    // The bare `base` store is the pre-fix global store that holds leaked data.
    // A bearer/legacy session must land on `base--legacy`, never back on `base`.
    const base = 'free-intelligence-conversations';
    expect(scopedStoreName(base, null)).toBe(`${base}--legacy`);
    expect(scopedStoreName(base, undefined)).toBe(`${base}--legacy`);
    expect(scopedStoreName(base, '')).toBe(`${base}--legacy`);
    expect(scopedStoreName(base, '   ')).toBe(`${base}--legacy`);
    expect(scopedStoreName(base, null)).not.toBe(base);
  });

  it('derives a DISTINCT name per identity — the leak fix invariant', () => {
    const a = scopedStoreName('free-intelligence-conversations', 'google-oauth2|aaa');
    const b = scopedStoreName('free-intelligence-conversations', 'google-oauth2|bbb');
    expect(a).not.toBe(b);
    expect(a).not.toBe('free-intelligence-conversations');
    expect(b).not.toBe('free-intelligence-conversations');
  });

  it('the legacy scope is distinct from any real identity', () => {
    const base = 'free-intelligence-conversations';
    expect(scopedStoreName(base, null)).not.toBe(scopedStoreName(base, 'legacy-user-sub'));
  });

  it('is stable for the same identity (memoization key)', () => {
    expect(scopedStoreName('base', 'sub-1')).toBe(scopedStoreName('base', 'sub-1'));
  });
});
