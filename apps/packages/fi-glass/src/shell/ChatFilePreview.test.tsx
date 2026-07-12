// @vitest-environment jsdom
/**
 * The upload chip must never TRAP the user.
 *
 * `pending_instructions` was folded into "processing": the chip spun a loader,
 * said "Procesando…" — and the cancel button was hidden precisely in that state.
 * Nothing was processing: the flow was waiting for the user to say how the
 * document should be used, and the UI that asked (ChatInstructionsPrompt) was
 * never mounted by anyone. So an upload parked there forever, with no way out.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { ChatFilePreview } from './ChatFilePreview';

const file = () => new File(['x'], 'estudio.pdf', { type: 'application/pdf' });
const cancelButton = () =>
  document.querySelector('button[aria-label="Cancelar"]') as HTMLButtonElement | null;

describe('<ChatFilePreview>', () => {
  afterEach(cleanup);

  it('waiting for the user is NOT "processing" — and stays cancellable', () => {
    render(
      <ChatFilePreview file={file()} status="pending_instructions" onCancel={vi.fn()} />,
    );
    expect(document.body.textContent).toContain('Elige cómo usarlo');
    expect(document.body.textContent).not.toContain('Procesando');
    // The escape hatch the old code hid exactly here.
    expect(cancelButton()).not.toBeNull();
  });

  it('real processing shows the loader and holds the cancel (work is in flight)', () => {
    render(<ChatFilePreview file={file()} status="processing" onCancel={vi.fn()} />);
    expect(document.body.textContent).toContain('Procesando');
    expect(cancelButton()).toBeNull();
  });

  it('an indexed document is done — no cancel, no spinner', () => {
    render(<ChatFilePreview file={file()} status="indexed" onCancel={vi.fn()} />);
    expect(document.body.textContent).toContain('Indexado');
    expect(cancelButton()).toBeNull();
  });

  it('a freshly picked file can always be dismissed', () => {
    render(<ChatFilePreview file={file()} status="selecting" onCancel={vi.fn()} />);
    expect(cancelButton()).not.toBeNull();
  });
});
