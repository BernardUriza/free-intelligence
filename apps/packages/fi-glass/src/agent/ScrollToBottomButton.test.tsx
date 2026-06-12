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

describe('ScrollToBottomButton', () => {
  it('renders default skin + placement with the default aria-label', () => {
    const html = renderToStaticMarkup(<ScrollToBottomButton onClick={() => {}} />);
    expect(html).toContain('aria-label="Ir al final"');
    expect(html).toContain('class="fi-scroll-to-bottom"');
    expect(html).toContain('position:absolute');
    expect(html).toContain('border-radius:9999px');
  });

  it('keeps placement + focus-ring class but drops the skin when a consumer class is set', () => {
    const html = renderToStaticMarkup(
      <ScrollToBottomButton onClick={() => {}} className="og-jump" label="Al fondo" />,
    );
    expect(html).toContain('class="fi-scroll-to-bottom og-jump"');
    expect(html).toContain('aria-label="Al fondo"');
    expect(html).toContain('position:absolute');
    expect(html).not.toContain('border-radius:9999px');
  });
});
