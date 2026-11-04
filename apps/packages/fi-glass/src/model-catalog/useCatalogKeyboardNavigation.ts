'use client';

import { useEffect, useRef, useState } from 'react';
import type { CatalogModel } from './types';

export interface UseCatalogKeyboardNavigationOptions {
  open: boolean;
  models: readonly CatalogModel[];
  installing: Record<string, number>;
  onInstall: (model: CatalogModel) => void;
}

function isEditable(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
}

/**
 * `/` focuses search; arrows and Enter drive the list only while the search box or the sheet itself
 * has focus, so a focused button, select or another dialog keeps its own keys.
 */
export function useCatalogKeyboardNavigation({ open, models, installing, onInstall }: UseCatalogKeyboardNavigationOptions) {
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const listRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setSelectedIndex(-1);
  }, [models.length]);

  useEffect(() => {
    if (!open) return;
    const ownsKey = (target: EventTarget | null) =>
      target === searchRef.current ||
      target === document.body ||
      target === listRef.current?.closest('[role="dialog"]');
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/') {
        if (isEditable(e.target)) return;
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (!ownsKey(e.target)) return;
      const total = models.length;
      if (total === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % total);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + total) % total);
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        const model = models[selectedIndex];
        if (model && !model.is_installed && !(model.id in installing)) {
          e.preventDefault();
          onInstall(model);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, models, selectedIndex, installing, onInstall]);

  useEffect(() => {
    if (selectedIndex < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll('[data-catalog-row]');
    items[selectedIndex]?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
  }, [selectedIndex]);

  return { selectedIndex, listRef, searchRef };
}
