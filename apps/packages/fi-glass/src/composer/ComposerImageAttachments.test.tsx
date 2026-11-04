// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ComposerImageChips } from './ComposerImageAttachments';

afterEach(cleanup);

const draft = { id: 'a', name: 'foto.png', dataUrl: 'data:image/png;base64,x' } as never;

describe('<ComposerImageChips>', () => {
  it('gives the remove control a 44px hit area around its 20px glyph', () => {
    render(<ComposerImageChips drafts={[draft]} onRemove={vi.fn()} />);
    const button = screen.getByRole('button', { name: /Quitar imagen/ });
    expect(button.style.width).toBe('2.75rem');
    expect(button.style.height).toBe('2.75rem');
    const glyph = button.firstElementChild as HTMLElement;
    expect(glyph.style.width).toBe('1.25rem');
  });

  it('removes the image it belongs to', () => {
    const onRemove = vi.fn();
    render(<ComposerImageChips drafts={[draft]} onRemove={onRemove} />);
    screen.getByRole('button', { name: /Quitar imagen/ }).click();
    expect(onRemove).toHaveBeenCalledWith('a');
  });
});
