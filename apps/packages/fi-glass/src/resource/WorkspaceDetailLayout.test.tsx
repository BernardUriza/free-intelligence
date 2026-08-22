// @vitest-environment jsdom
/**
 * The two-column workspace detail (FIGLASS-PROJECTS-PAGE-1).
 *
 * The rail is OPTIONAL and must not leave an empty 352px gutter behind when a
 * workspace has nothing to put in it. When present it is a complementary
 * landmark with a name, because "aside" alone tells a screen reader nothing.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { WorkspaceDetailLayout } from './WorkspaceDetailLayout';

afterEach(cleanup);

describe('WorkspaceDetailLayout', () => {
  it('renders no rail element at all when none was given', () => {
    const { container } = render(<WorkspaceDetailLayout>main</WorkspaceDetailLayout>);

    expect(container.querySelector('.fi-workspace-rail')).toBeNull();
    expect(screen.getByText('main')).toBeTruthy();
  });

  it('exposes the rail as a named complementary landmark', () => {
    render(
      <WorkspaceDetailLayout rail={<p>knowledge</p>} railLabel="Conocimiento">
        main
      </WorkspaceDetailLayout>,
    );

    expect(screen.getByRole('complementary', { name: 'Conocimiento' })).toBeTruthy();
  });

  it('lets a consumer override the rail width through the token, not a hard literal', () => {
    const { container } = render(
      <WorkspaceDetailLayout rail={<p>r</p>} railWidth={280}>
        main
      </WorkspaceDetailLayout>,
    );

    const root = container.querySelector('.fi-workspace-detail') as HTMLElement;
    expect(root.style.getPropertyValue('--fi-resource-rail-width')).toBe('280px');
  });

  it('accepts a string width verbatim', () => {
    const { container } = render(
      <WorkspaceDetailLayout rail={<p>r</p>} railWidth="20rem">
        main
      </WorkspaceDetailLayout>,
    );

    const root = container.querySelector('.fi-workspace-detail') as HTMLElement;
    expect(root.style.getPropertyValue('--fi-resource-rail-width')).toBe('20rem');
  });
});

describe('the mobile stacking rule', () => {
  /**
   * jsdom does no layout, so this cannot claim "measured at 374px" — the pixel
   * measurement [[mobile-viewport-ux]] requires belongs to the consumer PR, where
   * a real page renders these. What IS pinnable here is that the rule exists and
   * hangs off the CANONICAL breakpoint rather than a literal someone retyped: a
   * rail that quietly kept its 352px on a phone would leave neither column usable.
   */
  it('stacks the rail under the main column at the canonical mobile breakpoint', async () => {
    const { ensureResourceStyle } = await import('./resourceStyle');
    const { FI_MOBILE_QUERY } = await import('../theme/breakpoints');
    ensureResourceStyle();

    const css = document.getElementById('fi-resource-style')?.textContent ?? '';
    const mobileBlock = css.slice(css.indexOf(`@media ${FI_MOBILE_QUERY}`));

    expect(mobileBlock).toContain('flex-direction: column');
    expect(mobileBlock).toContain('width: 100%');
  });

  it('injects the stylesheet exactly once no matter how many primitives mount', () => {
    render(
      <WorkspaceDetailLayout rail={<p>r</p>}>
        <WorkspaceDetailLayout>nested</WorkspaceDetailLayout>
      </WorkspaceDetailLayout>,
    );

    expect(document.querySelectorAll('#fi-resource-style')).toHaveLength(1);
  });
});
