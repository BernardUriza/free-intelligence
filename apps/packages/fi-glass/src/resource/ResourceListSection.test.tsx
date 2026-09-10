// @vitest-environment jsdom
/**
 * ResourceListSection — la sección de lista de un workspace.
 *
 * El módulo no sabe QUÉ se lista: og118 pone conversaciones de un proyecto y
 * fi-glass no aprende esa palabra. Estado vacío y de carga son children del
 * consumidor a propósito — un componente con su propio "no hay nada todavía" ya
 * eligió un idioma.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceListSection, ResourceListItems, ResourceListRow } from './ResourceListSection';

describe('ResourceListSection', () => {
  it('un título string se envuelve en h2; un nodo se usa tal cual', () => {
    const { container, rerender } = render(
      <ResourceListSection title="Conversaciones">x</ResourceListSection>,
    );
    expect(container.querySelector('h2')?.textContent).toBe('Conversaciones');

    rerender(<ResourceListSection title={<h3>Otro</h3>}>x</ResourceListSection>);
    expect(container.querySelector('h2')).toBeNull();
    expect(container.querySelector('h3')?.textContent).toBe('Otro');
  });

  it('la acción de cabecera y la etiqueta accesible llegan del consumidor', () => {
    const { container } = render(
      <ResourceListSection title="t" ariaLabel="Conversaciones del proyecto" actionSlot={<button>Nueva</button>}>
        x
      </ResourceListSection>,
    );
    expect(container.querySelector('.fi-resource-list-head button')?.textContent).toBe('Nueva');
    expect(container.querySelector('section')?.getAttribute('aria-label')).toBe(
      'Conversaciones del proyecto',
    );
  });

  it('la fila expone título y meta, y meta se omite si no hay', () => {
    const { container, rerender } = render(
      <ResourceListItems><ResourceListRow title="Cotización" meta="hace 2 h" /></ResourceListItems>,
    );
    expect(container.querySelector('.fi-resource-list-row-title')?.textContent).toBe('Cotización');
    expect(container.querySelector('.fi-resource-list-row-meta')?.textContent).toBe('hace 2 h');

    rerender(<ResourceListItems><ResourceListRow title="Sin fecha" /></ResourceListItems>);
    expect(container.querySelector('.fi-resource-list-row-meta')).toBeNull();
  });

  it('la fila es un botón real: se selecciona con teclado igual que con click', () => {
    const onSelect = vi.fn();
    render(<ResourceListItems><ResourceListRow title="Cotización" onSelect={onSelect} /></ResourceListItems>);
    const fila = screen.getByRole('button', { name: /Cotización/ });
    fireEvent.click(fila);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
