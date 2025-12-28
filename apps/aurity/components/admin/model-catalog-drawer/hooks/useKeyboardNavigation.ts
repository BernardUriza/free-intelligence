'use client';

import { useState, useEffect, useRef } from 'react';
import type { CatalogModel } from '@/lib/api/catalog';

interface UseKeyboardNavigationOptions {
  isOpen: boolean;
  onClose: () => void;
  displayedModels: CatalogModel[];
  installingModels: Record<string, number>;
  onInstall: (model: CatalogModel) => void;
}

export function useKeyboardNavigation({
  isOpen,
  onClose,
  displayedModels,
  installingModels,
  onInstall,
}: UseKeyboardNavigationOptions) {
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const listRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Reset selection when models change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [displayedModels.length]);

  // Keyboard event handler
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      const totalModels = displayedModels.length;
      if (totalModels === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % totalModels);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + totalModels) % totalModels);
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        const model = displayedModels[selectedIndex];
        if (model && !model.is_installed && !(model.id in installingModels)) {
          onInstall(model);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, displayedModels, selectedIndex, installingModels, onInstall]);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[data-model-item]');
      items[selectedIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex]);

  return {
    selectedIndex,
    listRef,
    searchInputRef,
  };
}
