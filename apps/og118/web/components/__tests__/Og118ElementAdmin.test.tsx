import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { Og118ElementAdmin } from '../Og118ElementAdmin';

const SLOTS = [
  { atomicNumber: 1, symbol: 'H', slug: 'hidrogeno', displayName: 'Hidrógeno' },
  { atomicNumber: 117, symbol: 'Ts', slug: 'teneso', displayName: 'Teneso' },
];

// 2026-10-28, app.og118.ai: picking slot 117 left the form named "Hidrógeno", id "hidrogeno".
describe('Og118ElementAdmin create', () => {
  it('names the new element after the slot the author picks', () => {
    render(<Og118ElementAdmin mode="create" onClose={vi.fn()} slots={SLOTS} onChanged={vi.fn()} />);
    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe('Hidrógeno');

    fireEvent.change(screen.getByLabelText(/^Casilla/), { target: { value: '117' } });

    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe('Teneso');
    expect((screen.getByLabelText(/^ID único/) as HTMLInputElement).value).toBe('teneso');
    expect((screen.getByLabelText(/^Casilla/) as HTMLSelectElement).value).toBe('117');
  });
});
