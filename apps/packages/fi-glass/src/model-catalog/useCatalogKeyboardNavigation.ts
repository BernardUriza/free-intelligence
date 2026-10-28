'use client';

import { useEffect, useRef, useState } from 'react';
import type { CatalogModel } from './types';

export interface UseCatalogKeyboardNavigationOptions {
  open: boolean;
  models: readonly CatalogModel[];
  installing: Record<string, number>;
  onInstall: (model: CatalogModel) => void;
}

/** `/` focuses search, arrows move the selection, Enter installs the selected row. */
export function useCatalogKeyboardNavigation({ open, models, installing, onInstall }: UseCatalogKeyboardNavigationOptions) {
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const listRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setSelectedIndex(-1);
  }, [models.length]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== searchRef.current) {
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
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
