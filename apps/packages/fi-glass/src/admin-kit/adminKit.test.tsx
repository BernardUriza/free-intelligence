// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AdminAlert, AdminButton, AdminSheet } from './controls';
import { ensureAdminKitStyle } from './adminKitStyle';
import { ensurePersonaAdminStyle } from '../persona-admin/personaAdminStyle';
import { ensureModelCatalogStyle } from '../model-catalog/modelCatalogStyle';

function rules(css: string) {
  return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(([, selector, body]) => ({ selector: selector.trim(), body }));
}

describe('admin-kit stylesheets', () => {
  ensureAdminKitStyle();
  ensurePersonaAdminStyle();
  ensureModelCatalogStyle();
  const sheets = ['fi-admin-kit-style', 'fi-persona-admin-style', 'fi-model-catalog-style'].map(
    (id) => [id, document.getElementById(id)?.textContent ?? ''] as const,
  );

  it.each(sheets)('%s is injected with balanced braces', (_id, css) => {
    expect(css.length).toBeGreaterThan(0);
    expect(css.split('{').length).toBe(css.split('}').length);
  });

  it.each(sheets)('%s never hides a form field', (_id, css) => {
    const hiding = rules(css).filter((r) => /display:\s*none/.test(r.body) && /-input\b/.test(r.selector));
    expect(hiding).toEqual([]);
  });
});

describe('admin-kit controls', () => {
  it('a sheet dismisses on Escape and on the backdrop, and carries the module class', () => {
    const onDismiss = vi.fn();
    const { container } = render(
      <AdminSheet onDismiss={onDismiss} labelledBy="t" className="fi-model-catalog" header={<h2 id="t">Hola</h2>}>
        cuerpo
      </AdminSheet>,
    );
    expect(screen.getByRole('dialog', { name: 'Hola' })).toBeTruthy();
    expect(container.querySelector('.fi-admin-overlay.fi-model-catalog')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.click(container.querySelector('.fi-admin-backdrop')!);
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });

  it('a button is a touch target that shows a spinner while loading', () => {
    render(<AdminButton loading>Guardar</AdminButton>);
    const button = screen.getByRole('button', { name: 'Guardar' });
    expect(button.className).toContain('fi-touch-target');
    expect(button.querySelector('.fi-admin-spin')).toBeTruthy();
  });

  it('an alert announces itself and keeps its action', () => {
    render(<AdminAlert action={<button type="button">Reintentar</button>}>Falló</AdminAlert>);
    expect(screen.getByRole('alert').textContent).toContain('Falló');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeTruthy();
  });
});
