/**
 * Tests for ScrollToBottomButton (B3-FIGLASS-12).
 *
 * Contract: placement (absolute, bottom-centered) is framework-owned and
 * SURVIVES a consumer className override — the consumer skins the button but
 * can never detach it from the transcript's bottom edge. Static SSR markup is
 * enough to pin the structural style + a11y label.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { ScrollToBottomButton } from './ScrollToBottomButton';
import { FI_TOUCH_TARGET_CLASS } from '../shell/touchTarget';

describe('ScrollToBottomButton', () => {
  it('renders default skin + placement with the default aria-label', () => {
    const html = renderToStaticMarkup(<ScrollToBottomButton onClick={() => {}} />);
    expect(html).toContain('aria-label="Ir al final"');
    expect(html).toContain('fi-scroll-to-bottom');
    expect(html).toContain('position:absolute');
    expect(html).toContain('border-radius:9999px');
  });

  it('keeps placement + focus-ring class but drops the skin when a consumer class is set', () => {
    const html = renderToStaticMarkup(
      <ScrollToBottomButton onClick={() => {}} className="og-jump" label="Al fondo" />,
    );
    expect(html).toContain('fi-scroll-to-bottom');
    expect(html).toContain('og-jump');
    expect(html).toContain('aria-label="Al fondo"');
    expect(html).toContain('position:absolute');
    expect(html).not.toContain('border-radius:9999px');
  });

  // B3-FIGLASS-TOKEN-LAYER-1 — this was the ONE interactive control in the
  // package that skipped the framework touch minimum, against the repo's own
  // rule ("touch targets >=44x44 SIEMPRE"). The class must ride in BOTH
  // branches: a consumer skinning the button cannot opt out of the minimum.
  it('carries the touch minimum whether or not the consumer skins it', () => {
    const bare = renderToStaticMarkup(<ScrollToBottomButton onClick={() => {}} />);
    const skinned = renderToStaticMarkup(
      <ScrollToBottomButton onClick={() => {}} className="og-jump" />,
    );
    expect(bare).toContain(FI_TOUCH_TARGET_CLASS);
    expect(skinned).toContain(FI_TOUCH_TARGET_CLASS);
  });
});
