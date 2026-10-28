/**
 * OG118-ELEMENTOS-ALTA — the form that claims a slot. Positive: the draft carries
 * the chosen slot, its persona id and the engine. Resistance: an engine refusal is
 * shown and the dialog stays open; with no DNA the submit stays disabled.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Og118ElementCreateDialog } from '../Og118ElementCreateDialog';
import { personaIdFor } from '../../lib/og118Element';

const SLOTS = [
  { atomicNumber: 86, symbol: 'Rn', slug: 'radon', displayName: 'Radón' },
  { atomicNumber: 87, symbol: 'Fr', slug: 'francio', displayName: 'Francio' },
];

describe('Og118ElementCreateDialog', () => {
  it('sends the slot, its persona id and the chosen engine', async () => {
    const onCreate = vi.fn().mockResolvedValue('francio');
    const onClose = vi.fn();
    render(<Og118ElementCreateDialog open slots={SLOTS} onClose={onClose} onCreate={onCreate} />);
    const user = userEvent.setup();

    await user.selectOptions(screen.getByLabelText('Casilla'), '87');
    await user.click(screen.getByLabelText('GPT-6 Astra (Codex)'));
    await user.type(screen.getByLabelText(/Alias/), 'fr, franki');
    await user.type(screen.getByLabelText(/Persona/), 'Eres Francio.');
    await user.click(screen.getByRole('button', { name: 'Crear elemento' }));

    expect(onCreate).toHaveBeenCalledWith({
      atomicNumber: 87,
      displayName: 'Francio',
      personaId: 'francio',
      description: '',
      aliases: ['fr', 'franki'],
      engine: 'codex',
      dna: 'Eres Francio.',
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('shows the server refusal and stays open', async () => {
    const onCreate = vi.fn().mockRejectedValue(new Error('slot 86 (Rn) is active, not empty'));
    const onClose = vi.fn();
    render(<Og118ElementCreateDialog open slots={SLOTS} onClose={onClose} onCreate={onCreate} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/Persona/), 'Eres Radón.');
    await user.click(screen.getByRole('button', { name: 'Crear elemento' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('is active, not empty');
    expect(onClose).not.toHaveBeenCalled();
  });

  it('keeps the submit disabled without a persona', () => {
    render(<Og118ElementCreateDialog open slots={SLOTS} onClose={vi.fn()} onCreate={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Crear elemento' })).toBeDisabled();
  });
});

describe('personaIdFor', () => {
  it('turns a slot slug into an id the engine accepts', () => {
    expect(personaIdFor('radon')).toBe('radon');
    expect(personaIdFor('Ástato-x')).toBe('astato_x');
  });
});
