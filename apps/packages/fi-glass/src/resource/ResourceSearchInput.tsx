'use client';

/**
 * fi-glass · the full-width search box above a resource grid.
 *
 * Controlled on purpose: the consumer owns the query, because the same string
 * usually drives more than this input (a result count, an empty state, a URL
 * param). An uncontrolled box would hide the query inside the framework and
 * force the consumer to mirror it.
 *
 * It filters nothing by itself — {@link filterByQuery} is exported beside it so
 * the consumer gets the matching rule without this component ever learning what
 * a row means.
 */

import { type ChangeEvent } from 'react';
import { FI_SEARCH_CLASS, useResourceStyle } from './resourceStyle';

export interface ResourceSearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** Required: a search box with no accessible name is unusable by a screen reader. */
  ariaLabel: string;
  className?: string;
}

export function ResourceSearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
  className,
}: ResourceSearchInputProps) {
  useResourceStyle();
  return (
    <input
      type="search"
      className={className ? `${FI_SEARCH_CLASS} ${className}` : FI_SEARCH_CLASS}
      value={value}
      placeholder={placeholder}
      aria-label={ariaLabel}
      onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
    />
  );
}

/**
 * Case- and accent-insensitive substring match over the fields a consumer names.
 *
 * Accent folding is not a nicety here: typing "papeleria" must find "Papelería",
 * and a Spanish-speaking user on a phone keyboard routinely omits the accent.
 * An empty query matches everything rather than nothing.
 */
export function filterByQuery<T>(items: T[], query: string, fields: (item: T) => (string | undefined)[]): T[] {
  const needle = fold(query);
  if (!needle) return items;
  return items.filter((item) =>
    fields(item).some((field) => fold(field ?? '').includes(needle)),
  );
}

function fold(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}
