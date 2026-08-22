// @vitest-environment jsdom
/**
 * The capacity meter (FIGLASS-PROJECTS-PAGE-1).
 *
 * The case that matters is UNBOUNDED. `max == null` travels the wire meaning "no
 * quota configured", and a meter that answered it with a percentage would
 * launder an honest unlimited into a comforting number. So: no bar, no
 * percentage, and the label is told `null` so the consumer writes real words.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { CapacityMeter } from './CapacityMeter';

afterEach(cleanup);

describe('CapacityMeter', () => {
  it('draws no bar and reports null to the label when there is no ceiling', () => {
    render(
      <CapacityMeter
        used={40}
        max={null}
        label={(p) => (p === null ? 'sin tope' : `${p}%`)}
      />,
    );

    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByText('sin tope')).toBeTruthy();
  });

  it('treats an absent max the same as an explicit null', () => {
    render(<CapacityMeter used={40} label={(p) => (p === null ? 'sin tope' : `${p}%`)} />);

    expect(screen.queryByRole('progressbar')).toBeNull();
  });

  it('reports the percentage on the progressbar when bounded', () => {
    render(<CapacityMeter used={25} max={100} label={(p) => `${p}%`} />);

    const bar = screen.getByRole('progressbar');
    expect(bar.getAttribute('aria-valuenow')).toBe('25');
    expect(bar.getAttribute('aria-valuemax')).toBe('100');
  });

  it('clamps a corpus that is over its lowered quota to a full bar', () => {
    render(<CapacityMeter used={300} max={100} label={(p) => `${p}%`} />);

    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('100');
    expect(screen.getByText('100%')).toBeTruthy();
  });

  it('a zero ceiling is FULL, not unlimited', () => {
    render(<CapacityMeter used={0} max={0} label={(p) => (p === null ? 'sin tope' : `${p}%`)} />);

    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('100');
  });

  it('an empty bounded corpus reads zero', () => {
    render(<CapacityMeter used={0} max={100} label={(p) => `${p}%`} />);

    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0');
  });
});
