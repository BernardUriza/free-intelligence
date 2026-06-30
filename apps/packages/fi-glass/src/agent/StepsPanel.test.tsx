import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';

import { StepsPanel } from './StepsPanel';

// slowThresholdMs={0} makes showSlowBanner true on the first render (elapsed=0 ≥ 0),
// so the banner is present in static markup without driving timers.
describe('StepsPanel "still working" banner', () => {
  const html = renderToStaticMarkup(
    <StepsPanel steps={[]} status="thinking" enableSlowBanner slowThresholdMs={0} />,
  );

  it('shows the reassurance text', () => {
    expect(html).toContain('Still working. This can take a second.');
  });

  it('reads as an in-progress (blue) state, NOT an amber error/warning', () => {
    expect(html).toMatch(/bg-sky-/);
    expect(html).toMatch(/text-sky-/);
    // the previous amber/warning styling must be gone — it read as an error
    expect(html).not.toMatch(/amber/);
  });

  it('uses an ANIMATED spinner, not a static warning triangle', () => {
    expect(html).toContain('animate-spin');
  });
});
