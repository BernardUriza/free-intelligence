// @vitest-environment jsdom
/**
 * EditableSection — el marco de vista⇄edición.
 *
 * Lo que se fija aquí es la frontera: el marco no tiene estado ni copy. og118
 * escribía esta forma DOS VECES en el mismo archivo (encabezado del workspace y
 * panel de instrucciones) con clases propias; si vuelve a divergir, es porque
 * alguien dejó de componer esto.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EditableSection } from './EditableSection';

describe('EditableSection', () => {
  it('en vista NO monta un formulario ni los campos de edición', () => {
    const { container } = render(
      <EditableSection editing={false} view={<p>Proyecto Fénix</p>}>
        <input aria-label="nombre" />
      </EditableSection>,
    );
    expect(screen.getByText('Proyecto Fénix')).toBeTruthy();
    expect(container.querySelector('form')).toBeNull();
    expect(screen.queryByLabelText('nombre')).toBeNull();
  });

  it('en edición monta el form con los campos y esconde la vista', () => {
    const { container } = render(
      <EditableSection editing view={<p>Proyecto Fénix</p>}>
        <input aria-label="nombre" />
      </EditableSection>,
    );
    expect(container.querySelector('form')).not.toBeNull();
    expect(screen.getByLabelText('nombre')).toBeTruthy();
    expect(screen.queryByText('Proyecto Fénix')).toBeNull();
  });

  it('envía por submit, así que Enter en un campo guarda', () => {
    const onSubmit = vi.fn((e) => e.preventDefault());
    const { container } = render(
      <EditableSection editing view={null} onSubmit={onSubmit} submitSlot={<button type="submit">ok</button>} />,
    );
    fireEvent.submit(container.querySelector('form')!);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('la fila de acciones y el error sólo existen cuando hay algo que poner', () => {
    const { container, rerender } = render(<EditableSection editing view={null} />);
    expect(container.querySelector('.fi-editable-actions')).toBeNull();
    expect(container.querySelector('.fi-editable-error')).toBeNull();

    rerender(
      <EditableSection editing view={null} submitSlot={<button>g</button>} error="No se pudo guardar." />,
    );
    expect(container.querySelector('.fi-editable-actions')).not.toBeNull();
    expect(screen.getByText('No se pudo guardar.')).toBeTruthy();
  });

  it('no trae copy propio: cada control es del consumidor', () => {
    const { container } = render(
      <EditableSection editing view={null} submitSlot={<button>Guardar</button>} cancelSlot={<button>Cancelar</button>} />,
    );
    const botones = [...container.querySelectorAll('button')].map((b) => b.textContent);
    expect(botones).toEqual(['Guardar', 'Cancelar']);
  });
});
