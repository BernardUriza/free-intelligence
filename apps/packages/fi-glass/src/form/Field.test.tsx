// @vitest-environment jsdom
/**
 * The wiring is the component.
 *
 * A field that is merely red when it is wrong is a field only sighted users can
 * fill. These tests hold the three connections a hand-written `<input>` almost
 * never gets right: the label points at the control, the hint and the error are
 * announced WITH it, and invalid is a state assistive tech can read — not a
 * border colour.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Field } from './Field';
import { Button } from './Button';
import { Checkbox, Select, TextInput } from './controls';

afterEach(cleanup);

describe('Field', () => {
  it('points the label at the control it labels', () => {
    render(
      <Field label="Peso">
        {(control) => <TextInput {...control} defaultValue="12" />}
      </Field>,
    );
    // getByLabelText only finds it if htmlFor/id actually connect.
    expect((screen.getByLabelText('Peso') as HTMLInputElement).value).toBe('12');
  });

  it('announces the hint and the error together with the control', () => {
    render(
      <Field label="Peso" hint="En kilogramos" error="Falta el peso">
        {(control) => <TextInput {...control} />}
      </Field>,
    );
    const input = screen.getByLabelText('Peso');
    const ids = (input.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);

    expect(ids).toHaveLength(2);
    const announced = ids.map((id) => document.getElementById(id)?.textContent);
    expect(announced).toContain('En kilogramos');
    expect(announced).toContain('Falta el peso');
  });

  it('marks the control invalid, and the error is a live region', () => {
    render(
      <Field label="Peso" error="Falta el peso">
        {(control) => <TextInput {...control} />}
      </Field>,
    );
    expect(screen.getByLabelText('Peso').getAttribute('aria-invalid')).toBe('true');
    expect(screen.getByRole('alert').textContent).toBe('Falta el peso');
  });

  it('says nothing about validity when there is no error', () => {
    render(
      <Field label="Peso" hint="En kilogramos">
        {(control) => <TextInput {...control} />}
      </Field>,
    );
    const input = screen.getByLabelText('Peso');
    // Not `aria-invalid="false"`: absent is the honest state, and a screen
    // reader that announces "invalid, false" on every field trains its user to
    // ignore the word.
    expect(input.hasAttribute('aria-invalid')).toBe(false);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('marks a required control for assistive tech, not only with an asterisk', () => {
    render(
      <Field label="Nombre" required>
        {(control) => <TextInput {...control} />}
      </Field>,
    );
    expect(screen.getByLabelText('Nombre').getAttribute('aria-required')).toBe('true');
  });

  it('gives every field its own ids so two on a page do not collide', () => {
    render(
      <>
        <Field label="Uno" hint="a">{(c) => <TextInput {...c} />}</Field>
        <Field label="Dos" hint="b">{(c) => <TextInput {...c} />}</Field>
      </>,
    );
    const uno = screen.getByLabelText('Uno').getAttribute('aria-describedby');
    const dos = screen.getByLabelText('Dos').getAttribute('aria-describedby');
    expect(uno).toBeTruthy();
    expect(uno).not.toBe(dos);
  });
});

describe('Button', () => {
  it('defaults to type=button, so an unmarked button never submits by accident', () => {
    render(<Button>Guardar</Button>);
    expect(screen.getByRole('button', { name: 'Guardar' }).getAttribute('type')).toBe('button');
  });

  it('still lets a real submit say so', () => {
    render(<Button type="submit">Enviar</Button>);
    expect(screen.getByRole('button', { name: 'Enviar' }).getAttribute('type')).toBe('submit');
  });

  it('dresses the tone without losing the consumer class', () => {
    render(<Button tone="danger" className="propia">Borrar</Button>);
    const b = screen.getByRole('button', { name: 'Borrar' });
    expect(b.className).toContain('fi-button-danger');
    expect(b.className).toContain('propia');
  });
});

describe('Select', () => {
  it('renders the options and reports the chosen value', () => {
    const onChange = vi.fn();
    render(
      <Field label="Formato">
        {(control) => (
          <Select
            {...control}
            value="general"
            onChange={onChange}
            options={[
              { value: 'general', label: 'General' },
              { value: 'pediatrica', label: 'Pediátrica' },
            ]}
          />
        )}
      </Field>,
    );
    const select = screen.getByLabelText('Formato') as HTMLSelectElement;
    expect(select.options).toHaveLength(2);
    fireEvent.change(select, { target: { value: 'pediatrica' } });
    expect(onChange).toHaveBeenCalled();
  });

  it('renders the placeholder as a disabled entry, never as a pickable value', () => {
    render(
      <Field label="Formato">
        {(control) => <Select {...control} placeholder="Elija…" options={[]} />}
      </Field>,
    );
    const first = (screen.getByLabelText('Formato') as HTMLSelectElement).options[0];
    expect(first.textContent).toBe('Elija…');
    expect(first.disabled).toBe(true);
  });
});

describe('Checkbox', () => {
  it('connects its own label without the consumer passing an id', () => {
    const onChange = vi.fn();
    render(<Checkbox label="Embarazo" onChange={onChange} />);
    fireEvent.click(screen.getByLabelText('Embarazo'));
    expect(onChange).toHaveBeenCalled();
  });
});
